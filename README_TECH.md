# 🔧 Technical README — PinkCat OCR Sort

> Internal reference for development, debugging, and AI-assisted work.  
> → [Presentation README](./README.md)

---

## 🤖 AI Instructions

- Wait for the author to specify what needs to be done before proceeding.
- Ask for the relevant files before making any modifications.
- All code additions (methods, variables, comments, strings) must be written in English. Do not introduce any hardcoded text in any other language.
- Every visible UI string must go through `core.i18n.tr()` and a key in `language/translations.csv` — never a literal string in a UI file. See §7.5.
- OCR logic lives exclusively in `core/ocr_engine.py` — do not add it to the GUI or worker layers.
- Processing runs in a background thread via `core/worker.py` — any UI update from the worker must go through thread-safe mechanisms (tkinter `after`).
- Name list is managed by `core/names_config.py` — do not hardcode names or load `names.txt` from other modules.
- Session file location (`session.json`) and the names list location (`names.txt`) are never hardcoded — both are resolved via `core/config_paths.py`. Do not read/write either file directly from `ui/app.py` or elsewhere; always go through `resolve_session_location()` / `resolve_names_location()` / `save_json_atomic()` / `save_text_atomic()` / `read_json()`.
- Never store the absolute path to `names.txt` inside `session.json` (or vice versa). `session.json` is meant to be cloud-synced and travel between computers; the names-file location is machine-local (its own pointer key, `names_path`, in the same `%APPDATA%` config). Mixing the two reintroduces the exact path-portability bug the pointer pattern exists to prevent.
- Colors come exclusively from `ui/theme.py`, which sources them from `gui/theme_loader.get_theme()`. No UI file should import `gui.themes.*` directly, and no new hardcoded hex color should be added outside `gui/themes/*.py`.
- `gui/theme_loader.py` and `gui/themes/{green,pink,pro}.py` are shared PinkCat Design System files — copy updates from `_Auditoría/gui/` rather than editing the palette values here.

---

## 1. Project Structure

```
PinkCat OCR Sort/
├── PinkCat OCR Sort.pyw     # Entry point (double-click to launch)
├── requirements.txt         # customtkinter, easyocr, Pillow
├── test_ocr.py              # Standalone OCR diagnostic tool (see §5)
├── language/
│   └── translations.csv     # i18n strings (key;Español;English)
├── gui/
│   ├── theme_loader.py      # get_theme(name) — shared Design System loader
│   └── themes/
│       ├── green.py
│       ├── pink.py          # default theme
│       └── pro.py
├── core/
│   ├── i18n.py               # Translation manager (load/tr/set_language)
│   ├── renamer.py            # Date-based renaming logic
│   ├── ocr_engine.py         # EasyOCR + fuzzy matching
│   ├── worker.py             # Background processing thread
│   ├── names_config.py       # names.txt load and save
│   └── config_paths.py       # Configurable session/names file locations (see §7)
├── ui/
│   ├── app.py                # Main window
│   ├── review_window.py      # Batch review window
│   ├── widgets.py            # Reusable CustomTkinter components
│   └── theme.py              # Bridges the app to the active Design System theme
└── ico/
    ├── PinkCat OCR Sort.ico  # App icon (window/taskbar)
    ├── PinkCat OCR Sort.png
    └── logo.png               # PinkCat mascot logo (title bar)
```

The real session file (`session.json` by default, but the name is user-chosen — see §7) no longer lives at a fixed path in the project folder. Its location is resolved at startup via `core/config_paths.py`.

---

## 2. Module Responsibilities

| File | Responsibility |
|---|---|
| `core/i18n.py` | Loads `language/translations.csv`; exposes `tr(key, **kwargs)`, `set_language()`, `on_language_changed()` for hot-reload |
| `core/renamer.py` | Rename files by creation date; handle name collisions with microseconds |
| `core/ocr_engine.py` | Run EasyOCR on each image; fuzzy-match result against `names.txt` |
| `core/worker.py` | Background thread — processes files without blocking the UI |
| `core/names_config.py` | Load, parse, and save the names list file (location resolved via `config_paths.py`) |
| `core/config_paths.py` | Resolve/store the real session file's AND the names file's location; local per-machine pointer in `%APPDATA%` (one key per file); atomic save (JSON and plain text) |
| `gui/theme_loader.py` | Shared PinkCat Design System entry point — `get_theme(name)` |
| `gui/themes/*.py` | Shared color palettes (green / pink / pro) — copied as-is from the Design System reference, not edited per-project |
| `ui/theme.py` | Resolves the active theme + project-specific typography/layout constants |
| `ui/app.py` | Main window — folder selection, options, log panels, session restore, settings menu |
| `ui/review_window.py` | Batch review window — thumbnails, dropdowns, confirm/cancel per batch of 8 |
| `ui/widgets.py` | Reusable CustomTkinter UI components |

---

## 3. Processing Flow

```
Source folder scan (root only, no subfolders)
        ↓
For each image:
  1. OCR reads visible text (ocr_engine.py)
  2. Fuzzy match against names.txt
        ↓
  Match found       → Destination/DetectedName/renamed_file
  Text but no match → Destination/_Unclassified/renamed_file
  No text detected  → Destination/Year/MM Month/DD/renamed_file
        ↓
[Review mode] → batch of 8 → review_window.py window → confirm or override
        ↓
File moved and renamed by creation date
```

---

## 4. Renaming Scheme

```
Format:    dd-MM-yyyy ; HH.mm.ss.ffff
Structure: Destination / Year / MM MonthName / DD / file

Example:   Destination / 2024 / 03 march / 15 / 15-03-2024 ; 14.32.11.0000.jpg
```

Name collision resolution: microseconds appended until a free name is found.

Month folder names (`core.renamer.MONTH_NAMES`) are fixed to English regardless of the active UI language — this is a file-naming convention, not a piece of UI text, so it isn't routed through `core.i18n`.

---

## 5. OCR System

- **Engine:** EasyOCR (downloaded on first run, ~300 MB)
- **GPU:** optional CUDA acceleration for NVIDIA GPUs
- **Matching:** fuzzy string comparison against `names.txt` using the configurable similarity threshold
- **Threshold guidance:** 40–60% for noisy/low-quality OCR; 80–100% for clean text

**Diagnostic tool:**
```bash
python test_ocr.py "path\to\image.jfif"
```
Prints the raw OCR text EasyOCR detected for a single image and the resulting fuzzy-match decision, using whatever `names.txt` is currently configured in `%APPDATA%`.

---

## 6. Log System

Two parallel logs in the right panel:

**Main log** — all operations, color-coded (colors come from the active theme's semantic keys, not hardcoded):
- `✅` `success` — processed correctly
- `⏭` `text_dim` — skipped (already correct)
- `⚠` `danger` — unclassified (OCR no match)
- `❌` `danger` — error
- `🔍` `info` — OCR analysis in progress

Detected folder names highlighted in a consistent color across runs (`ui.widgets.LogPanel.name_color()` — domain-specific rotating palette, explicitly out of scope for the shared Design System).

**Unclassified log** — only files sent to `_Unclassified`, with similarity percentage highlighted in amber.

---

## 7. Configurable File Locations (Session & Names List)

Two files no longer have a fixed default path in the project folder: the session file (`session.json`) and the names list (`names.txt`). Both are resolved at startup through `core/config_paths.py`, so either can live inside a cloud-synced folder (Google Drive, Dropbox…) and follow the user between computers. Same pattern used across other PinkCat projects.

Three pieces, applied independently to **each** file:

1. **Manual, mandatory location on first use.** There is no automatic default path for either file. On startup, `resolve_session_location()` and `resolve_names_location()` each check for a valid local pointer (see below); if none exists for that file, a modal dialog forces the user to pick one of two clear actions — **"Choose existing file"** or **"Create new file"** — before that file is used. The dialog can't be dismissed without choosing (window-close button is disabled). The chosen file's name is free — it doesn't have to be `session.json` / `names.txt`.

2. **Fixed local pointer, one per computer**, stored at:
   ```
   %APPDATA%\PinkCatOCRSort\config.json
   ```
   One JSON file, two independent keys:
   ```json
   { "session_path": "...", "names_path": "..." }
   ```
   This pointer is **not synced** — each machine keeps its own, pointing at wherever *that* machine sees the synced folder (the absolute path can differ between computers even when they point at the same underlying content).

   **Important:** the absolute path to `names.txt` must never be stored inside `session.json` (or vice versa) — `session.json` itself is meant to be cloud-synced and travel between machines, so embedding another machine-specific absolute path inside it would silently reintroduce the exact portability problem this pattern exists to solve. Each file's location lives only in the local pointer.

3. **Atomic save of both files.** `save_json_atomic()` (for `session.json`) and `save_text_atomic()` (for `names.txt`) always write to a temporary file (`<name>.tmp`) in the same folder, then call `os.replace()` to the final name — never write directly over the live file. This prevents a sync client from uploading a half-written version if it detects the change mid-write.

**Key functions (`core/config_paths.py`):**

| Function | Purpose |
|---|---|
| `resolve_session_location(parent)` | Entry point for the session file. Returns a valid `Path`, prompting the user if needed. |
| `resolve_names_location(parent, create_initial)` | Entry point for the names file. `create_initial` (normally `names_config.create_sample`) populates a newly created file with example names. |
| `peek_session_settings()` | Best-effort read of `session.json` without forcing the first-use dialog — used at startup to pick the UI language/theme before the main window is built. |
| `read_pointer(key)` / `save_pointer(key, path)` | Read/write one key (`"session_path"` or `"names_path"`) in the local `%APPDATA%` pointer. |
| `save_json_atomic(path, data)` | tmp + `os.replace()` atomic write for JSON. |
| `save_text_atomic(path, content)` | tmp + `os.replace()` atomic write for plain text. |
| `read_json(path)` | Plain JSON read helper. |

`ui/app.py` no longer hardcodes either path. `__init__` withdraws the window, resolves `self._session_path` and `self._names_path` via the functions above, then shows the window and proceeds. `_save_session()` / `_restore_session()` no longer read/write the names file path at all — its location is resolved independently at startup and updated via `save_pointer("names_path", ...)` whenever the user picks a different file manually (browse button, or "CREATE SAMPLE").

`session.json` also stores the active `"language"` and `"theme"` keys (see §7.5 and §8).

---

## 7.5. i18n (Internationalization)

- Every visible UI string lives in `language/translations.csv` (`;`-separated: `key;Español;English`), loaded once at startup by `core.i18n.load_translations()`.
- `core.i18n.tr(key, **kwargs)` looks up the active-language string and `.format()`s it with the given keyword arguments. Falls back to English, then to the raw key, if a translation is missing.
- Language switching is hot: `core.i18n.set_language(name)` updates the active language and calls every callback registered via `core.i18n.on_language_changed()`. `ui/app.py` registers `MainWindow.refresh_language()`, which re-reads `tr()` for every static label/button and re-derives any dynamic status text (names status, threshold hint, etc.) — no widgets are destroyed or recreated.
- The active language is persisted in `session.json` under `"language"` and restored on startup.
- Dynamic log lines assembled deep in `core/worker.py` and `core/ocr_engine.py` (e.g. "OCR: ... -> ... (NN% similarity)") are also translation keys with placeholders — not string-formatted in the caller's language directly — so the activity log is fully translated too.
- The bootstrap "choose session/names file" dialogs in `core/config_paths.py` run before any session data (including the saved language) can be read, so they are intentionally left in English rather than routed through `core.i18n` — a documented, narrow exception.
- Minimum languages present: Español, English.

---

## 8. Design System / Theming

- Colors and corner radii come from the shared PinkCat Design System (`gui/theme_loader.get_theme(name)` + `gui/themes/{green,pink,pro}.py`), read once at startup by `ui/theme.py`. Typography sizes, padding, and window size stay project-specific (outside the theme), per the Design System.
- The active theme name is read from `session.json["theme"]` (`peek_session_settings()`), defaulting to `pink` — the shared default — when no session exists yet.
- Selecting a different theme from **Settings → Theme** (top menu) saves the choice immediately but only takes effect after restarting the app, matching the Design System's documented behavior (unlike language, theme changes are not hot-reloaded).
- No UI file imports `gui.themes.*` directly; everything goes through `ui.theme`, which re-exports the resolved palette as module-level constants (`ACCENT`, `SUCCESS`, `DANGER`, etc.).
- The PinkCat mascot logo (`ico/logo.png`) is shown in the top-right corner of the app's title bar in every theme, including Professional.

---

## 9. Pending Tasks

None currently tracked.

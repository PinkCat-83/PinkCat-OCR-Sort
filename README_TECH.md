# 🔧 Technical README — PinkCat OCR Sort

> Internal reference for development, debugging, and AI-assisted work.  
> → [Presentation README](./README.md)

---

## 🤖 AI Instructions

- Wait for the author to specify what needs to be done before proceeding.
- Ask for the relevant files before making any modifications.
- OCR logic lives exclusively in `core/ocr_engine.py` — do not add it to the GUI or worker layers.
- Processing runs in a background thread via `core/worker.py` — any UI update from the worker must go through thread-safe mechanisms (tkinter `after` or queue).
- Name list is managed by `core/nombres_config.py` — do not hardcode names or load `nombres.txt` from other modules.
- Session file location (`sesion.json`) and the names list location (`nombres.txt`) are never hardcoded — both are resolved via `core/config_paths.py`. Do not read/write either file directly from `ui/app.py` or elsewhere; always go through `resolver_ubicacion_sesion()` / `resolver_ubicacion_nombres()` / `guardar_json_atomico()` / `guardar_texto_atomico()` / `leer_json()`.
- Never store the absolute path to `nombres.txt` inside `sesion.json` (or vice versa). `sesion.json` is meant to be cloud-synced and travel between computers; the names-file location is machine-local (its own pointer key, `ruta_nombres`, in the same `%APPDATA%` config). Mixing the two reintroduces the exact path-portability bug the pointer pattern exists to prevent.

---

## 1. Project Structure

```
PinkCat OCR Sort/
├── organizar.pyw           # Entry point (double-click to launch)
├── nombres.txt             # Name list for OCR matching (user-editable)
├── requirements.txt
├── core/
│   ├── renamer.py          # Date-based renaming logic
│   ├── ocr_engine.py       # EasyOCR + fuzzy matching
│   ├── worker.py           # Background processing thread
│   ├── nombres_config.py   # nombres.txt load and save
│   └── config_paths.py     # Configurable session-file location (see §7)
└── ui/
    ├── app.py              # Main window
    ├── revisor.py          # Batch review window
    ├── widgets.py          # Reusable UI components
    └── theme.py            # Color palette and typography
```

The real session file (`sesion.json` by default, but the name is user-chosen — see §7) no longer lives at a fixed path in the project folder. Its location is resolved at startup via `core/config_paths.py`.

---

## 2. Module Responsibilities

| File | Responsibility |
|---|---|
| `core/renamer.py` | Rename files by creation date; handle name collisions with microseconds |
| `core/ocr_engine.py` | Run EasyOCR on each image; fuzzy-match result against `nombres.txt` |
| `core/worker.py` | Background thread — processes files without blocking the UI |
| `core/nombres_config.py` | Load, parse, and save the names list file (location resolved via `config_paths.py`, no fixed default anymore) |
| `core/config_paths.py` | Resolve/store the real session file's AND the names file's location; local per-machine pointer in `%APPDATA%` (one key per file); atomic save (JSON and plain text) |
| `ui/app.py` | Main window — folder selection, options, log panels, session restore |
| `ui/revisor.py` | Batch review window — thumbnails, dropdowns, confirm/cancel per batch of 8 |
| `ui/widgets.py` | Reusable UI components |
| `ui/theme.py` | Color palette and typography constants |

---

## 3. Processing Flow

```
Source folder scan (root only, no subfolders)
        ↓
For each image:
  1. OCR reads visible text (ocr_engine.py)
  2. Fuzzy match against nombres.txt
        ↓
  Match found       → Destination/DetectedName/renamed_file
  Text but no match → Destination/_Sin clasificar/renamed_file
  No text detected  → Destination/Year/MM Month/DD/renamed_file
        ↓
[Review mode] → batch of 8 → revisor.py window → confirm or override
        ↓
File moved and renamed by creation date
```

---

## 4. Renaming Scheme

```
Format:    dd-MM-yyyy ; HH.mm.ss.ffff
Structure: Destination / Year / MM MonthName / DD / file

Example:   Destination / 2024 / 03 marzo / 15 / 15-03-2024 ; 14.32.11.0000.jpg
```

Name collision resolution: microseconds appended until a free name is found.

---

## 5. OCR System

- **Engine:** EasyOCR (downloaded on first run, ~300 MB)
- **GPU:** optional CUDA acceleration for NVIDIA GPUs
- **Matching:** fuzzy string comparison against `nombres.txt` using the configurable similarity threshold
- **Threshold guidance:** 40–60% for noisy/low-quality OCR; 80–100% for clean text

**Diagnostic tool:**
```bash
python test_ocr.py "path\to\image.jfif"
```

---

## 6. Log System

Two parallel logs in the right panel:

**Main log** — all operations, color-coded:
- `✅` Green — processed correctly
- `⏭` Grey — skipped (already correct)
- `⚠` Amber — unclassified (OCR no match)
- `❌` Red — error
- `🔍` Blue — OCR analysis in progress

Detected folder names highlighted in a consistent color across runs.

**Unclassified log** — only files sent to `_Sin clasificar`, with similarity percentage highlighted in amber.

---

## 7. Configurable File Locations (Session & Names List)

Two files no longer have a fixed default path in the project folder: the session file (`sesion.json`) and the names list (`nombres.txt`). Both are resolved at startup through `core/config_paths.py`, so either can live inside a cloud-synced folder (Google Drive, Dropbox…) and follow the user between computers. Same pattern used across other projects (e.g. Git Manager).

Three pieces, applied independently to **each** file:

1. **Manual, mandatory location on first use.** There is no automatic default path for either file. On startup, `resolver_ubicacion_sesion()` and `resolver_ubicacion_nombres()` each check for a valid local pointer (see below); if none exists for that file, a modal dialog forces the user to pick one of two clear actions — **"Elegir archivo existente"** or **"Crear archivo nuevo"** — before that file is used. The dialog can't be dismissed without choosing (window-close button is disabled). The chosen file's name is free — it doesn't have to be `sesion.json` / `nombres.txt`.

2. **Fixed local pointer, one per computer**, stored at:
   ```
   %APPDATA%\PinkCat OCR Sort\config.json
   ```
   One JSON file, two independent keys:
   ```json
   { "ruta_sesion": "...", "ruta_nombres": "..." }
   ```
   This pointer is **not synced** — each machine keeps its own, pointing at wherever *that* machine sees the synced folder (the absolute path can differ between computers even when they point at the same underlying content).

   **Important:** the absolute path to `nombres.txt` must never be stored inside `sesion.json` (or vice versa) — `sesion.json` itself is meant to be cloud-synced and travel between machines, so embedding another machine-specific absolute path inside it would silently reintroduce the exact portability problem this pattern exists to solve. Each file's location lives only in the local pointer.

3. **Atomic save of both files.** `guardar_json_atomico()` (for `sesion.json`) and `guardar_texto_atomico()` (for `nombres.txt`) always write to a temporary file (`<name>.tmp`) in the same folder, then call `os.replace()` to the final name — never write directly over the live file. This prevents a sync client from uploading a half-written version if it detects the change mid-write.

**Key functions (`core/config_paths.py`):**

| Function | Purpose |
|---|---|
| `resolver_ubicacion_sesion(parent)` | Entry point for the session file. Returns a valid `Path`, prompting the user if needed. |
| `resolver_ubicacion_nombres(parent, crear_inicial)` | Entry point for the names file. `crear_inicial` (normally `nombres_config.crear_ejemplo`) populates a newly created file with example names. |
| `leer_puntero(clave)` / `guardar_puntero(clave, ruta)` | Read/write one key (`"ruta_sesion"` or `"ruta_nombres"`) in the local `%APPDATA%` pointer. |
| `guardar_json_atomico(ruta, datos)` | tmp + `os.replace()` atomic write for JSON. |
| `guardar_texto_atomico(ruta, contenido)` | tmp + `os.replace()` atomic write for plain text. |
| `leer_json(ruta)` | Plain JSON read helper. |

`ui/app.py` no longer hardcodes either path. `__init__` withdraws the window, resolves `self._sesion_path` and `self._nombres_path` via the functions above, then shows the window and proceeds. `_guardar_sesion()` / `_restaurar_sesion()` no longer read/write `archivo_nombres` at all — the names-file location is resolved independently at startup and updated via `guardar_puntero("ruta_nombres", ...)` whenever the user picks a different file manually (browse button, or "CREAR EJEMPLO").

---

## 8. Pending Tasks

- [ ] **i18n (internationalization).** Add a `language/` subfolder at the project root containing a `translations.csv` file with the app's UI strings and their translations. Scope/format not decided yet — to be defined when picked up.

"""
core/config_paths.py
Configurable location for the app's external files (the real session.json
and the real names.txt) plus a local per-computer pointer, following the
same pattern already validated in other projects (Git Manager):

  1. Manual, mandatory location on first use.
     There is no automatic default path. If there is no valid pointer on
     this computer for a given file, the user is forced to pick an
     existing one or create a new one before continuing.

  2. Fixed local pointer, one per computer, stored at
     %APPDATA%/PinkCatOCRSort/config.json
     Contains only absolute paths (one key per managed file:
     "session_path", "names_path"). This pointer is NOT synced between
     computers: each machine keeps its own, pointing at wherever THAT
     machine sees the synced folder.

     IMPORTANT: this is why neither absolute path should ever be stored
     inside the other file that does travel synced (e.g. do not store
     names.txt's path inside session.json) — that would reintroduce the
     exact portability problem this module solves.

  3. Atomic save of the real data: always write to a temporary file
     (same name + .tmp) in the same folder, then os.replace() to the
     final name, so a sync client (Drive, Dropbox…) never sees a
     half-written version. Applies to both JSON (session.json) and plain
     text (names.txt).
"""
import json
import os
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Callable

APP_NAME = "PinkCatOCRSort"


# ──────────────────────────────────────────────────────────────────────────
#  Local pointer (%APPDATA%) — a single config.json with several keys
# ──────────────────────────────────────────────────────────────────────────

def _appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        # Fallback outside Windows (development/testing)
        base = str(Path.home() / "AppData" / "Roaming")
    folder = Path(base) / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _pointer_file() -> Path:
    return _appdata_dir() / "config.json"


def _read_full_pointer() -> dict:
    pointer_file = _pointer_file()
    if not pointer_file.exists():
        return {}
    try:
        return json.loads(pointer_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_pointer(key: str) -> Path | None:
    """Absolute path stored under `key` in the local pointer, or None if it
    doesn't exist, is corrupted, or the file it points to is gone."""
    path_str = _read_full_pointer().get(key)
    if not path_str:
        return None
    path = Path(path_str)
    return path if path.exists() else None


def save_pointer(key: str, path: Path) -> None:
    """Saves the absolute path under `key` in the %APPDATA% pointer. This
    file is local to this machine and must NOT be synced."""
    data = _read_full_pointer()
    data[key] = str(Path(path).resolve())
    save_json_atomic(_pointer_file(), data)


# ──────────────────────────────────────────────────────────────────────────
#  Atomic read/write of the real data files
# ──────────────────────────────────────────────────────────────────────────

def save_json_atomic(path: Path, data: dict) -> None:
    """Writes `data` (JSON) to `path` atomically: first to a temp file in
    the same folder, then os.replace() to the final name."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def save_text_atomic(path: Path, content: str) -> None:
    """Same as save_json_atomic but for plain text (e.g. names.txt):
    tmp + os.replace()."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────────────
#  Location resolution (public entry points)
# ──────────────────────────────────────────────────────────────────────────

def resolve_session_location(parent: tk.Misc) -> Path:
    """Session file (session.json): local pointer under "session_path"."""
    path = read_pointer("session_path")
    if path is not None:
        return path
    path = _first_use_dialog(
        parent,
        window_title=f"{APP_NAME} — Initial setup",
        main_message="No session file is configured on this computer yet.",
        detail_message="Choose an existing session file (for example, inside your\n"
                        "Google Drive or Dropbox folder) or create a new one. The\n"
                        "choice will be remembered on this computer.",
        filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        default_name="session.json",
        create_initial=lambda new_path: save_json_atomic(new_path, {}),
    )
    save_pointer("session_path", path)
    return path


def resolve_names_location(parent: tk.Misc, create_initial: Callable[[Path], None]) -> Path:
    """Names list (names.txt): local pointer under "names_path".
    `create_initial` receives the chosen path and must write the sample
    content (normally core.names_config.create_sample)."""
    path = read_pointer("names_path")
    if path is not None:
        return path
    path = _first_use_dialog(
        parent,
        window_title=f"{APP_NAME} — Names list",
        main_message="No names (.txt) file is configured on this computer yet.",
        detail_message="Choose an existing .txt file (for example, inside your\n"
                        "Google Drive or Dropbox folder) or create a new one with\n"
                        "sample names. The choice will be remembered on this\n"
                        "computer.",
        filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        default_name="names.txt",
        create_initial=create_initial,
    )
    save_pointer("names_path", path)
    return path


def peek_session_settings() -> dict:
    """Best-effort read of the session file's contents without forcing the
    first-use dialog. Used at startup to pick the UI language/theme before
    the main window is built. Returns {} if no session is configured yet
    or it can't be read."""
    path = read_pointer("session_path")
    if path is None:
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _first_use_dialog(
    parent: tk.Misc,
    *,
    window_title: str,
    main_message: str,
    detail_message: str,
    filetypes: list[tuple[str, str]],
    default_name: str,
    create_initial: Callable[[Path], None],
) -> Path:
    """Generic modal dialog: forces the user to pick an existing file or
    create a new one. Cannot be closed without choosing (close button
    disabled)."""
    result: dict = {"path": None}
    win = tk.Toplevel(parent)
    win.title(window_title)
    win.resizable(False, False)
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda: None)  # choice is mandatory

    tk.Label(win, text=main_message, font=("Segoe UI", 10, "bold"),
             justify="left").pack(padx=20, pady=(20, 6))
    tk.Label(win, text=detail_message, font=("Segoe UI", 9),
             justify="left").pack(padx=20, pady=(0, 16))

    buttons = tk.Frame(win)
    buttons.pack(padx=20, pady=(0, 20))

    def choose_existing():
        path = filedialog.askopenfilename(
            parent=win,
            title=f"Select the existing file ({default_name})",
            filetypes=filetypes,
        )
        if path:
            result["path"] = Path(path)
            win.destroy()

    def create_new():
        extension = Path(default_name).suffix or None
        path = filedialog.asksaveasfilename(
            parent=win,
            title=f"Create the file ({default_name})",
            defaultextension=extension,
            initialfile=default_name,
            filetypes=filetypes,
        )
        if path:
            path_p = Path(path)
            if not path_p.exists():
                create_initial(path_p)
            result["path"] = path_p
            win.destroy()

    tk.Button(buttons, text="Choose existing file", width=24,
              command=choose_existing).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Create new file", width=20,
              command=create_new).pack(side="left")

    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = win.winfo_width(), win.winfo_height()
    win.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    parent.wait_window(win)
    # win cannot be closed without choosing, but for robustness we repeat
    # the dialog if for some reason there's still no path.
    if result["path"] is None:
        return _first_use_dialog(
            parent,
            window_title=window_title,
            main_message=main_message,
            detail_message=detail_message,
            filetypes=filetypes,
            default_name=default_name,
            create_initial=create_initial,
        )
    return result["path"]

"""
core/renamer.py
Renaming and date-based organizing logic.
Python equivalent of the Rename_Fast.ps1 script.
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


# File extensions to ignore (scripts, the program's own executables)
IGNORED_EXTENSIONS = {".ps1", ".pyw", ".py"}

# Pattern of an already-correct name: "dd-MM-yyyy ; HH.mm.ss.ffff"
CORRECT_NAME_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4} ; \d{2}\.\d{2}\.\d{2}\.\d{4}$")

# Month names used in the destination folder structure. Fixed to English
# regardless of the active UI language — this is a file-naming convention
# (part of the renaming scheme documented in the README), not a piece of
# UI text, so it isn't routed through core.i18n.
MONTH_NAMES = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december"
}


def get_creation_date(path: Path) -> datetime:
    """Returns the file's creation date (or modification date on Linux)."""
    stat = path.stat()
    # st_birthtime exists on Windows; on Linux we fall back to st_mtime
    ts = getattr(stat, "st_birthtime", None) or stat.st_mtime
    return datetime.fromtimestamp(ts)


def build_subfolder(root_dest: Path, date: datetime) -> Path:
    """
    Builds the subfolder path following the scheme:
      root_dest / year / "MM monthName" / "dd"
    """
    year = str(date.year)
    month_num = date.strftime("%m")
    month_name = MONTH_NAMES[date.month]
    day = date.strftime("%d")
    return root_dest / year / f"{month_num} {month_name}" / day


def format_name(date: datetime, extension: str) -> str:
    """Generates the new file name: 'dd-MM-yyyy ; HH.mm.ss.ffff'."""
    # ffff = tenths of a microsecond (4 digits)
    ffff = f"{date.microsecond // 100:04d}"
    base = date.strftime(f"%d-%m-%Y ; %H.%M.%S.{ffff}")
    return base + extension


def resolve_conflict(subfolder: Path, name: str, date: datetime, extension: str):
    """
    If the name already exists at the destination, increments ticks
    (100ns = 1 tick) until a free name is found. Returns (new_path, used_date).
    """
    candidate_path = subfolder / name
    from datetime import timedelta

    while candidate_path.exists():
        # Add 1000 ticks like the PS script (~100 µs)
        date = date + timedelta(microseconds=100)
        name = format_name(date, extension)
        candidate_path = subfolder / name

    return candidate_path, date


def is_already_correct(file: Path, expected_subfolder: Path) -> bool:
    """Checks whether the file already has the correct name and location."""
    name_without_ext = file.stem
    in_correct_folder = file.parent == expected_subfolder
    correct_name = bool(CORRECT_NAME_PATTERN.match(name_without_ext))
    return correct_name and in_correct_folder


def process_file(file: Path, root_dest: Path, ocr_name: str | None = None):
    """
    Processes a single file:
      - If there's an OCR name  → Dest/DetectedName/renamed_file
      - If there's no name      → Dest/Year/MM Month/DD/renamed_file

    Returns a dict with the result info for the log.
    """
    extension = file.suffix.lower()

    if extension in IGNORED_EXTENSIONS:
        return {"status": "ignored", "file": file.name, "reason": "ignored extension"}

    date = get_creation_date(file)
    new_name = format_name(date, extension)

    if ocr_name:
        # With OCR name: flat folder Dest/DetectedName/
        subfolder = root_dest / ocr_name
    else:
        # Without OCR name: date-based structure
        subfolder = build_subfolder(root_dest, date)
        # Check whether it's already in its correct place
        if is_already_correct(file, subfolder):
            return {"status": "skipped", "file": file.name, "reason": "already correct"}

    new_path, _ = resolve_conflict(subfolder, new_name, date, extension)

    subfolder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file), str(new_path))

    return {
        "status": "ok",
        "file": file.name,
        "destination": str(new_path.relative_to(root_dest)),
        "ocr_name": ocr_name,
    }

"""
core/names_config.py
Loads and saves the names list from an external .txt file.

File format: one name per line, blank lines and lines starting with #
are ignored. Example:
    # Family
    Ana
    Carlos
    Grandma Mari

This file's location no longer has an automatic default path: it is
resolved at startup via core.config_paths.resolve_names_location()
(local pointer in %APPDATA%, mandatory selection on first use). Every
function in this module requires the explicit path.
"""
from pathlib import Path

from core.config_paths import save_text_atomic

# Kept only as a reference value (e.g. suggested name in "save as"
# dialogs). No longer used as a default path.
DEFAULT_NAMES_FILE = Path("names.txt")


def load_names(path: Path) -> list[str]:
    """
    Reads the .txt file and returns the cleaned list of names.
    Returns an empty list if the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        return []

    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def save_names(names: list[str], path: Path):
    """Writes the names list to the .txt file atomically (tmp +
    os.replace()), so a half-written version is never left behind if the
    file lives in a synced folder."""
    content = "# Names list for PinkCat OCR Sort\n"
    content += "# One name per line. Lines starting with # are comments.\n\n"
    content += "\n".join(names)
    save_text_atomic(Path(path), content)


def create_sample(path: Path):
    """Creates a sample file if it doesn't exist."""
    path = Path(path)
    if not path.exists():
        save_names(["Ana", "Carlos", "Grandma Mari", "Vacation"], path)

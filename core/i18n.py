"""
core/i18n.py
Minimal translation manager. Loads language/translations.csv and exposes
tr(key, **kwargs) for looking up the active-language string. Widgets that
show text register a callback via on_language_changed() so they can
reconfigure their labels in place when the language changes (hot reload,
no restart required).
"""
import csv
from pathlib import Path
from typing import Callable

DEFAULT_LANGUAGE = "English"

_translations: dict[str, dict[str, str]] = {}
_languages: list[str] = []
_current_language = DEFAULT_LANGUAGE
_listeners: list[Callable[[], None]] = []


def load_translations(csv_path: Path) -> None:
    """Loads the translations CSV (key;Lang1;Lang2;... with ';' separator)."""
    global _translations, _languages
    csv_path = Path(csv_path)
    translations: dict[str, dict[str, str]] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        languages = header[1:]
        for row in reader:
            if not row or not row[0]:
                continue
            key, values = row[0], row[1:]
            translations[key] = dict(zip(languages, values))
    _translations = translations
    _languages = languages


def available_languages() -> list[str]:
    return list(_languages)


def get_language() -> str:
    return _current_language


def set_language(language: str) -> None:
    """Switches the active language and notifies every registered listener
    so already-built widgets can refresh their text without a restart."""
    global _current_language
    if language not in _languages or language == _current_language:
        return
    _current_language = language
    for callback in list(_listeners):
        callback()


def on_language_changed(callback: Callable[[], None]) -> None:
    _listeners.append(callback)


def tr(key: str, **kwargs) -> str:
    """Returns the string for `key` in the active language, formatted with
    `kwargs`. Falls back to DEFAULT_LANGUAGE, then to the key itself."""
    entry = _translations.get(key)
    if not entry:
        return key
    text = entry.get(_current_language) or entry.get(DEFAULT_LANGUAGE)
    if text is None:
        text = next(iter(entry.values()), key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text

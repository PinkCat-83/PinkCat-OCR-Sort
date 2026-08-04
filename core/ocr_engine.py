"""
core/ocr_engine.py
OCR engine based on EasyOCR with fuzzy matching against the names list.
"""
import re
from difflib import SequenceMatcher
from pathlib import Path

from core.i18n import tr

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
                     ".webp", ".jfif", ".heic", ".gif"}

# Destination folder when OCR finds text but it doesn't match any name
UNCLASSIFIED_FOLDER = "_Unclassified"

# Minimum similarity threshold to accept a match (0.0-1.0)
SIMILARITY_THRESHOLD = 0.72

_reader_cache = None
_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _get_reader(gpu: bool = False):
    global _reader_cache
    if _reader_cache is None:
        import easyocr
        _reader_cache = easyocr.Reader(["es", "en"], gpu=gpu)
    return _reader_cache


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _load_image(path: Path):
    """
    Loads the image as a numpy array via PIL, avoiding the issue where
    cv2.imread returns None for .jfif and other formats on Windows.
    """
    import numpy as np
    from PIL import Image
    img = Image.open(path).convert("RGB")
    return np.array(img)


def extract_text(path: Path, gpu: bool = False) -> tuple[list[str], str]:
    """
    Returns (list_of_texts, error).
    error is "" if everything went fine, or the exception message if it failed.
    """
    if not is_image(path) or not path.exists():
        return [], ""
    try:
        reader = _get_reader(gpu=gpu)
        img = _load_image(path)
        results = reader.readtext(img, detail=0)
        return [r.strip() for r in results if r.strip()], ""
    except Exception as e:
        return [], str(e)


def _similarity(a: str, b: str) -> float:
    """Similarity ratio between two strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _best_match(ocr_text: str, names: list[str]) -> tuple[str | None, float]:
    """
    Compares ocr_text against every name in the list and returns
    (best_name, score). Score between 0.0 and 1.0.
    """
    best = None
    best_score = 0.0
    for name in names:
        score = _similarity(ocr_text, name)
        if score > best_score:
            best_score = score
            best = name
    return best, best_score


def find_name(path: Path, names: list[str], gpu: bool = False) -> tuple[str | None, str]:
    """
    Extracts OCR text from the image and compares it against the names list.

    Returns (destination_folder, log_reason):
      - Match >= threshold        → (name_from_list, 'OCR: "X" -> "Y" (NN% similarity)')
      - Text found but no match   → (UNCLASSIFIED_FOLDER, "text detected, no match")
      - No text found in image    → (None, "no OCR text")
    """
    if not names:
        return None, tr("ocr_names_empty")

    texts, ocr_error = extract_text(path, gpu=gpu)
    if ocr_error:
        return None, tr("ocr_error", error=ocr_error)
    if not texts:
        return None, tr("ocr_no_text")

    # Try every OCR line against every name; keep the best overall match
    best_folder = None
    best_score = 0.0
    best_ocr_text = ""

    for text in texts:
        folder, score = _best_match(text, names)
        if score > best_score:
            best_score = score
            best_folder = folder
            best_ocr_text = text

    pct = int(best_score * 100)

    if best_score >= SIMILARITY_THRESHOLD:
        reason = tr("ocr_match", text=best_ocr_text, folder=best_folder, pct=pct)
        return best_folder, reason
    else:
        reason = tr("ocr_no_match", text=best_ocr_text, pct=pct,
                     threshold=int(SIMILARITY_THRESHOLD * 100))
        return UNCLASSIFIED_FOLDER, reason


def reset_reader():
    global _reader_cache
    _reader_cache = None

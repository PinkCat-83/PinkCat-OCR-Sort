"""
core/ocr_engine.py
Motor OCR basado en EasyOCR con fuzzy matching contra lista de nombres.
"""
import re
from difflib import SequenceMatcher
from pathlib import Path

# Extensiones de imagen soportadas
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
                      ".webp", ".jfif", ".heic", ".gif"}

# Carpeta de destino cuando hay texto OCR pero no encaja con ningún nombre
CARPETA_SIN_CLASIFICAR = "_Sin clasificar"

# Umbral mínimo de similitud para aceptar un match (0.0-1.0)
UMBRAL_SIMILITUD = 0.72

_reader_cache = None
_CHARS_INVALIDOS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _get_reader(gpu: bool = False):
    global _reader_cache
    if _reader_cache is None:
        import easyocr
        _reader_cache = easyocr.Reader(["es", "en"], gpu=gpu)
    return _reader_cache


def es_imagen(ruta: Path) -> bool:
    return ruta.suffix.lower() in EXTENSIONES_IMAGEN


def _cargar_imagen(ruta: Path):
    """
    Carga la imagen como numpy array via PIL, evitando el problema de
    cv2.imread que devuelve None en .jfif y otros formatos en Windows.
    """
    import numpy as np
    from PIL import Image
    img = Image.open(ruta).convert("RGB")
    return np.array(img)


def extraer_texto(ruta: Path, gpu: bool = False) -> tuple[list[str], str]:
    """
    Devuelve (lista_de_textos, error).
    error es "" si todo fue bien, o el mensaje de excepción si falló.
    """
    if not es_imagen(ruta) or not ruta.exists():
        return [], ""
    try:
        reader = _get_reader(gpu=gpu)
        img = _cargar_imagen(ruta)
        resultados = reader.readtext(img, detail=0)
        return [r.strip() for r in resultados if r.strip()], ""
    except Exception as e:
        return [], str(e)


def _similitud(a: str, b: str) -> float:
    """Ratio de similitud entre dos strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _mejor_match(texto_ocr: str, nombres: list[str]) -> tuple[str | None, float]:
    """
    Compara texto_ocr contra cada nombre de la lista y devuelve
    (mejor_nombre, score). Score entre 0.0 y 1.0.
    """
    mejor = None
    mejor_score = 0.0
    for nombre in nombres:
        score = _similitud(texto_ocr, nombre)
        if score > mejor_score:
            mejor_score = score
            mejor = nombre
    return mejor, mejor_score


def buscar_nombre(ruta: Path, nombres: list[str], gpu: bool = False) -> tuple[str | None, str]:
    """
    Extrae texto OCR de la imagen y lo compara contra la lista de nombres.

    Devuelve (carpeta_destino, motivo_log):
      - Si hay match ≥ umbral   → (nombre_de_la_lista, "NombreOCR → NombreLista (score%)")
      - Si hay texto pero no encaja → (CARPETA_SIN_CLASIFICAR, "texto detectado, sin match")
      - Si no hay texto en la imagen → (None, "sin texto OCR")
    """
    if not nombres:
        return None, "lista de nombres vacía"

    textos, error_ocr = extraer_texto(ruta, gpu=gpu)
    if error_ocr:
        return None, f"error OCR: {error_ocr}"
    if not textos:
        return None, "sin texto OCR"

    # Probar cada línea OCR contra todos los nombres; quedarse con el mejor global
    mejor_carpeta = None
    mejor_score = 0.0
    mejor_ocr = ""

    for texto in textos:
        carpeta, score = _mejor_match(texto, nombres)
        if score > mejor_score:
            mejor_score = score
            mejor_carpeta = carpeta
            mejor_ocr = texto

    pct = int(mejor_score * 100)

    if mejor_score >= UMBRAL_SIMILITUD:
        motivo = f'OCR: "{mejor_ocr}" → "{mejor_carpeta}" ({pct}% similitud)'
        return mejor_carpeta, motivo
    else:
        motivo = f'OCR: "{mejor_ocr}" sin match suficiente ({pct}% < {int(UMBRAL_SIMILITUD*100)}%)'
        return CARPETA_SIN_CLASIFICAR, motivo


def reset_reader():
    global _reader_cache
    _reader_cache = None

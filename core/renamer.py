"""
core/renamer.py
Lógica de renombrado y organización por fecha de creación.
Equivalente Python del script Rename_Fast.ps1
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


# Extensiones de archivo a ignorar (scripts, ejecutables del propio programa)
EXTENSIONES_IGNORADAS = {".ps1", ".pyw", ".py"}

# Patrón de nombre ya correcto: "dd-MM-yyyy ; HH.mm.ss.ffff"
PATRON_CORRECTO = re.compile(r"^\d{2}-\d{2}-\d{4} ; \d{2}\.\d{2}\.\d{2}\.\d{4}$")

# Nombres de meses en español
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def obtener_fecha_creacion(ruta: Path) -> datetime:
    """Devuelve la fecha de creación del archivo (o modificación en Linux)."""
    stat = ruta.stat()
    # En Windows existe st_birthtime; en Linux usamos st_mtime como fallback
    ts = getattr(stat, "st_birthtime", None) or stat.st_mtime
    return datetime.fromtimestamp(ts)


def construir_subcarpeta(destino_raiz: Path, fecha: datetime) -> Path:
    """
    Construye la ruta de subcarpeta según el esquema:
      destino_raiz / año / "MM nombreMes" / "dd"
    """
    año = str(fecha.year)
    mes_num = fecha.strftime("%m")
    mes_nombre = MESES_ES[fecha.month]
    dia = fecha.strftime("%d")
    return destino_raiz / año / f"{mes_num} {mes_nombre}" / dia


def formatear_nombre(fecha: datetime, extension: str) -> str:
    """Genera el nuevo nombre de archivo: 'dd-MM-yyyy ; HH.mm.ss.ffff'."""
    # ffff = décimas de microsegundo (4 dígitos)
    ffff = f"{fecha.microsecond // 100:04d}"
    base = fecha.strftime(f"%d-%m-%Y ; %H.%M.%S.{ffff}")
    return base + extension


def resolver_conflicto(subcarpeta: Path, nombre: str, fecha: datetime, extension: str):
    """
    Si el nombre ya existe en destino, incrementa ticks (100ns = 1 tick)
    hasta encontrar un nombre libre. Devuelve (nueva_ruta, fecha_usada).
    """
    ruta_candidata = subcarpeta / nombre
    from datetime import timedelta
    delta_tick = timedelta(microseconds=0.1)  # 1 tick = 100 ns ≈ 0.1 µs

    while ruta_candidata.exists():
        # Añadir 1000 ticks como el script PS (≈ 100 µs)
        fecha = fecha + timedelta(microseconds=100)
        nombre = formatear_nombre(fecha, extension)
        ruta_candidata = subcarpeta / nombre

    return ruta_candidata, fecha


def ya_esta_correcto(archivo: Path, subcarpeta_esperada: Path) -> bool:
    """Comprueba si el archivo ya tiene nombre y ubicación correctos."""
    nombre_sin_ext = archivo.stem
    en_carpeta_correcta = archivo.parent == subcarpeta_esperada
    nombre_correcto = bool(PATRON_CORRECTO.match(nombre_sin_ext))
    return nombre_correcto and en_carpeta_correcta


def procesar_archivo(archivo: Path, destino_raiz: Path, nombre_ocr: str | None = None):
    """
    Procesa un único archivo:
      - Si hay nombre OCR  → Destino/NombreDetectado/archivo_renombrado
      - Si no hay nombre   → Destino/Año/MM Mes/DD/archivo_renombrado

    Devuelve un dict con info del resultado para el log.
    """
    extension = archivo.suffix.lower()

    if extension in EXTENSIONES_IGNORADAS:
        return {"estado": "ignorado", "archivo": archivo.name, "motivo": "extensión ignorada"}

    fecha = obtener_fecha_creacion(archivo)
    nuevo_nombre = formatear_nombre(fecha, extension)

    if nombre_ocr:
        # Con nombre OCR: carpeta plana Destino/NombreDetectado/
        subcarpeta = destino_raiz / nombre_ocr
    else:
        # Sin nombre OCR: estructura por fecha
        subcarpeta = construir_subcarpeta(destino_raiz, fecha)
        # Comprobar si ya está en su sitio correcto
        if ya_esta_correcto(archivo, subcarpeta):
            return {"estado": "omitido", "archivo": archivo.name, "motivo": "ya está correcto"}

    nueva_ruta, _ = resolver_conflicto(subcarpeta, nuevo_nombre, fecha, extension)

    subcarpeta.mkdir(parents=True, exist_ok=True)
    shutil.move(str(archivo), str(nueva_ruta))

    return {
        "estado": "ok",
        "archivo": archivo.name,
        "destino": str(nueva_ruta.relative_to(destino_raiz)),
        "nombre_ocr": nombre_ocr,
    }

"""
core/nombres_config.py
Carga y guarda la lista de nombres desde un archivo .txt externo.

Formato del archivo: un nombre por línea, líneas vacías y con # ignoradas.
Ejemplo:
    # Familia
    Ana
    Carlos
    Abuela Mari

La ubicación de este archivo ya NO tiene una ruta por defecto automática:
se resuelve en el arranque vía core.config_paths.resolver_ubicacion_nombres()
(puntero local en %APPDATA%, con selección obligatoria en el primer uso).
Todas las funciones de este módulo requieren la ruta explícita.
"""
from pathlib import Path

from core.config_paths import guardar_texto_atomico

# Mantenido solo como valor de referencia (p. ej. nombre sugerido en
# diálogos de "guardar como"). Ya NO se usa como ruta por defecto.
ARCHIVO_NOMBRES_DEFAULT = Path("nombres.txt")


def cargar_nombres(ruta: Path) -> list[str]:
    """
    Lee el archivo .txt y devuelve la lista de nombres limpios.
    Si el archivo no existe devuelve lista vacía.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return []

    nombres = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            nombres.append(linea)
    return nombres


def guardar_nombres(nombres: list[str], ruta: Path):
    """Escribe la lista de nombres al archivo .txt de forma atómica
    (tmp + os.replace()), para no dejar nunca una versión a medio escribir
    si el archivo vive en una carpeta sincronizada."""
    contenido = "# Lista de nombres para PinkCat OCR Sort\n"
    contenido += "# Un nombre por línea. Las líneas con # son comentarios.\n\n"
    contenido += "\n".join(nombres)
    guardar_texto_atomico(Path(ruta), contenido)


def crear_ejemplo(ruta: Path):
    """Crea un archivo de ejemplo si no existe."""
    ruta = Path(ruta)
    if not ruta.exists():
        guardar_nombres(["Ana", "Carlos", "Abuela Mari", "Vacaciones"], ruta)

"""
gui/theme_loader.py
Punto único de acceso a la paleta de colores activa.

Regla de oro: ningún archivo de UI importa `gui.themes.green` /
`gui.themes.pink` / `gui.themes.pro` directamente. Siempre se llama a
get_theme().

Este archivo vive en gui/theme_loader.py, con las paletas en
gui/themes/{green,pink,pro}.py — copiar tal cual, sin regenerar.
"""

import importlib

DEFAULT_THEME = "pink"


def get_theme(name: str = DEFAULT_THEME) -> dict:
    """
    Devuelve el diccionario THEME del tema solicitado.
    Si el nombre no existe (typo en el JSON de config, tema borrado, etc.),
    cae de vuelta a DEFAULT_THEME en vez de lanzar una excepción.
    """
    try:
        module = importlib.import_module(f"gui.themes.{name}")
    except ModuleNotFoundError:
        module = importlib.import_module(f"gui.themes.{DEFAULT_THEME}")
    return module.THEME

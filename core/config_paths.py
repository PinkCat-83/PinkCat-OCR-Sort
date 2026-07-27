"""
core/config_paths.py
Ubicación configurable de los archivos externos de la app (sesion.json real
y nombres.txt real) y puntero local por ordenador, siguiendo el mismo
patrón ya validado en otros proyectos (Git Manager):

  1. Ubicación manual y obligatoria en el primer uso.
     No hay ninguna ruta por defecto automática. Si no hay un puntero
     válido en este ordenador para ese archivo, se obliga a elegir uno
     existente o crear uno nuevo antes de continuar.

  2. Puntero fijo y local por ordenador en
     %APPDATA%/PinkCat OCR Sort/config.json
     Contiene solo rutas absolutas (una clave por archivo gestionado:
     "ruta_sesion", "ruta_nombres"). Este puntero NO se sincroniza entre
     ordenadores: cada máquina tiene el suyo, apuntando a dónde ESA
     máquina ve la carpeta sincronizada.

     IMPORTANTE: por eso ninguna ruta absoluta de estos archivos debe
     guardarse dentro de otro archivo que sí viaje sincronizado (p. ej.
     no guardar la ruta de nombres.txt dentro de sesion.json) — eso
     reintroduciría el mismo problema de portabilidad entre ordenadores
     que este módulo resuelve.

  3. Guardado atómico de los datos reales: se escribe siempre a un
     archivo temporal (mismo nombre + .tmp) en la misma carpeta y luego
     se hace os.replace() al nombre final, para que un cliente de
     sincronización (Drive, Dropbox…) nunca vea una versión a medio
     escribir. Vale tanto para JSON (sesion.json) como para texto plano
     (nombres.txt).
"""
import json
import os
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Callable

NOMBRE_APP = "PinkCat OCR Sort"


# ──────────────────────────────────────────────────────────────────────────
#  Puntero local (%APPDATA%) — un único config.json con varias claves
# ──────────────────────────────────────────────────────────────────────────

def _dir_appdata() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        # Fallback fuera de Windows (desarrollo/pruebas)
        base = str(Path.home() / "AppData" / "Roaming")
    carpeta = Path(base) / NOMBRE_APP
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _archivo_puntero() -> Path:
    return _dir_appdata() / "config.json"


def _leer_puntero_completo() -> dict:
    ruta_puntero = _archivo_puntero()
    if not ruta_puntero.exists():
        return {}
    try:
        return json.loads(ruta_puntero.read_text(encoding="utf-8"))
    except Exception:
        return {}


def leer_puntero(clave: str) -> Path | None:
    """Ruta absoluta guardada bajo `clave` en el puntero local, o None si
    no existe, está corrupto, o el archivo al que apunta ya no está ahí."""
    ruta_str = _leer_puntero_completo().get(clave)
    if not ruta_str:
        return None
    ruta = Path(ruta_str)
    return ruta if ruta.exists() else None


def guardar_puntero(clave: str, ruta: Path) -> None:
    """Guarda en %APPDATA% la ruta absoluta bajo `clave`. Este archivo es
    local a esta máquina y NO debe sincronizarse."""
    datos = _leer_puntero_completo()
    datos[clave] = str(Path(ruta).resolve())
    guardar_json_atomico(_archivo_puntero(), datos)


# ──────────────────────────────────────────────────────────────────────────
#  Guardado / lectura atómica de los datos reales
# ──────────────────────────────────────────────────────────────────────────

def guardar_json_atomico(ruta: Path, datos: dict) -> None:
    """Escribe `datos` (JSON) en `ruta` de forma atómica: primero a un
    archivo temporal en la misma carpeta y luego os.replace() al nombre
    final."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ruta)


def guardar_texto_atomico(ruta: Path, contenido: str) -> None:
    """Igual que guardar_json_atomico pero para texto plano (p. ej.
    nombres.txt): tmp + os.replace()."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(contenido, encoding="utf-8")
    os.replace(tmp, ruta)


def leer_json(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────────────
#  Resolución de ubicación (puntos de entrada públicos)
# ──────────────────────────────────────────────────────────────────────────

def resolver_ubicacion_sesion(parent: tk.Misc) -> Path:
    """Sesión (sesion.json): puntero local bajo la clave "ruta_sesion"."""
    ruta = leer_puntero("ruta_sesion")
    if ruta is not None:
        return ruta
    ruta = _dialogo_primer_uso(
        parent,
        titulo_ventana=f"{NOMBRE_APP} — Configuración inicial",
        mensaje_principal="No se encontró un archivo de sesión configurado en este ordenador.",
        mensaje_detalle="Elige un archivo de sesión existente (por ejemplo, dentro de tu\n"
                         "carpeta de Google Drive o Dropbox) o crea uno nuevo. La elección\n"
                         "se recordará en este ordenador.",
        filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
        nombre_por_defecto="sesion.json",
        crear_inicial=lambda ruta_nueva: guardar_json_atomico(ruta_nueva, {}),
    )
    guardar_puntero("ruta_sesion", ruta)
    return ruta


def resolver_ubicacion_nombres(parent: tk.Misc, crear_inicial: Callable[[Path], None]) -> Path:
    """Lista de nombres (nombres.txt): puntero local bajo la clave
    "ruta_nombres". `crear_inicial` recibe la ruta elegida y debe escribir
    el contenido de ejemplo (normalmente core.nombres_config.crear_ejemplo)."""
    ruta = leer_puntero("ruta_nombres")
    if ruta is not None:
        return ruta
    ruta = _dialogo_primer_uso(
        parent,
        titulo_ventana=f"{NOMBRE_APP} — Lista de nombres",
        mensaje_principal="No se encontró una lista de nombres (.txt) configurada en este ordenador.",
        mensaje_detalle="Elige un archivo .txt existente (por ejemplo, dentro de tu\n"
                         "carpeta de Google Drive o Dropbox) o crea uno nuevo con\n"
                         "nombres de ejemplo. La elección se recordará en este ordenador.",
        filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        nombre_por_defecto="nombres.txt",
        crear_inicial=crear_inicial,
    )
    guardar_puntero("ruta_nombres", ruta)
    return ruta


def _dialogo_primer_uso(
    parent: tk.Misc,
    *,
    titulo_ventana: str,
    mensaje_principal: str,
    mensaje_detalle: str,
    filetypes: list[tuple[str, str]],
    nombre_por_defecto: str,
    crear_inicial: Callable[[Path], None],
) -> Path:
    """Diálogo modal genérico: obliga a elegir un archivo existente o crear
    uno nuevo. No se puede cerrar sin elegir (X deshabilitada)."""
    resultado: dict = {"ruta": None}
    win = tk.Toplevel(parent)
    win.title(titulo_ventana)
    win.resizable(False, False)
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda: None)  # elección obligatoria

    tk.Label(win, text=mensaje_principal, font=("Segoe UI", 10, "bold"),
             justify="left").pack(padx=20, pady=(20, 6))
    tk.Label(win, text=mensaje_detalle, font=("Segoe UI", 9),
             justify="left").pack(padx=20, pady=(0, 16))

    botones = tk.Frame(win)
    botones.pack(padx=20, pady=(0, 20))

    def elegir_existente():
        ruta = filedialog.askopenfilename(
            parent=win,
            title=f"Selecciona el archivo existente ({nombre_por_defecto})",
            filetypes=filetypes,
        )
        if ruta:
            resultado["ruta"] = Path(ruta)
            win.destroy()

    def crear_nuevo():
        extension = Path(nombre_por_defecto).suffix or None
        ruta = filedialog.asksaveasfilename(
            parent=win,
            title=f"Crea el archivo ({nombre_por_defecto})",
            defaultextension=extension,
            initialfile=nombre_por_defecto,
            filetypes=filetypes,
        )
        if ruta:
            ruta_p = Path(ruta)
            if not ruta_p.exists():
                crear_inicial(ruta_p)
            resultado["ruta"] = ruta_p
            win.destroy()

    tk.Button(botones, text="Elegir archivo existente", width=24,
              command=elegir_existente).pack(side="left", padx=(0, 8))
    tk.Button(botones, text="Crear archivo nuevo", width=20,
              command=crear_nuevo).pack(side="left")

    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = win.winfo_width(), win.winfo_height()
    win.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    parent.wait_window(win)
    # win no puede cerrarse sin elegir, pero por robustez repetimos el
    # diálogo si por algún motivo no hay ruta.
    if resultado["ruta"] is None:
        return _dialogo_primer_uso(
            parent,
            titulo_ventana=titulo_ventana,
            mensaje_principal=mensaje_principal,
            mensaje_detalle=mensaje_detalle,
            filetypes=filetypes,
            nombre_por_defecto=nombre_por_defecto,
            crear_inicial=crear_inicial,
        )
    return resultado["ruta"]

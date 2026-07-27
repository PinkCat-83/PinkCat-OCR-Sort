"""
ui/widgets.py
Componentes reutilizables con estilo industrial oscuro.
"""
import tkinter as tk
from tkinter import ttk
from ui.theme import *


# ── Botón estilizado ───────────────────────────────────────────────────────────

class BotonAccion(tk.Frame):
    """Botón con estilo flat oscuro y efecto hover."""

    def __init__(self, parent, texto, comando=None, estilo="normal", ancho=None, **kwargs):
        super().__init__(parent, bg=BG_BASE, **kwargs)

        colores = {
            "normal":   (BG_CARD, FG_PRIMARY, BG_HOVER),
            "primario": (ACCENT_DIM, ACCENT, ACCENT_DARK),
            "peligro":  (RED_DIM, RED, "#3d1515"),
            "exito":    (GREEN_DIM, GREEN, "#1a3d2a"),
        }
        self._bg, self._fg, self._hover = colores.get(estilo, colores["normal"])
        self._comando = comando

        kw = {"width": ancho} if ancho else {}
        self._btn = tk.Label(
            self,
            text=texto,
            bg=self._bg,
            fg=self._fg,
            font=FONT_UI,
            padx=14,
            pady=6,
            cursor="hand2",
            relief="flat",
            **kw,
        )
        self._btn.pack(fill="x")

        self._btn.bind("<Enter>", lambda e: self._btn.config(bg=self._hover))
        self._btn.bind("<Leave>", lambda e: self._btn.config(bg=self._bg))
        self._btn.bind("<Button-1>", self._click)

    def _click(self, event):
        if self._comando:
            self._comando()

    def config_texto(self, texto):
        self._btn.config(text=texto)

    def habilitar(self, activo: bool):
        if activo:
            self._btn.config(fg=self._fg, cursor="hand2")
            self._btn.bind("<Button-1>", self._click)
        else:
            self._btn.config(fg=FG_MUTED, cursor="arrow")
            self._btn.unbind("<Button-1>")


# ── Entrada de ruta ────────────────────────────────────────────────────────────

class EntradaRuta(tk.Frame):
    """Campo de texto + botón examinar para rutas de carpeta."""

    def __init__(self, parent, etiqueta, placeholder="", comando_examinar=None, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)

        # Etiqueta
        tk.Label(self, text=etiqueta.upper(), font=FONT_UI_SM,
                 bg=BG_PANEL, fg=FG_SECONDARY).pack(anchor="w", pady=(0, 3))

        # Contenedor input + botón
        fila = tk.Frame(self, bg=BG_INPUT, highlightbackground=BORDER,
                        highlightthickness=1)
        fila.pack(fill="x")

        self.var = tk.StringVar()
        self._entry = tk.Entry(
            fila,
            textvariable=self.var,
            font=FONT_MONO,
            bg=BG_INPUT,
            fg=FG_PRIMARY,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=8, pady=7)

        if placeholder:
            self._set_placeholder(placeholder)

        if comando_examinar:
            btn = tk.Label(
                fila,
                text="  ···  ",
                font=("Consolas", 9, "bold"),
                bg=ACCENT_DIM,
                fg=ACCENT,
                cursor="hand2",
                pady=7,
                padx=4,
            )
            btn.pack(side="right")
            btn.bind("<Button-1>", lambda e: comando_examinar())
            btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT, fg=BG_BASE))
            btn.bind("<Leave>", lambda e: btn.config(bg=ACCENT_DIM, fg=ACCENT))

    def _set_placeholder(self, texto):
        if not self.var.get():
            self._entry.insert(0, texto)
            self._entry.config(fg=FG_MUTED)

        def on_focus_in(e):
            if self._entry.get() == texto:
                self._entry.delete(0, "end")
                self._entry.config(fg=FG_PRIMARY)

        def on_focus_out(e):
            if not self._entry.get():
                self._entry.insert(0, texto)
                self._entry.config(fg=FG_MUTED)

        self._entry.bind("<FocusIn>", on_focus_in)
        self._entry.bind("<FocusOut>", on_focus_out)

    def get(self) -> str:
        return self.var.get()

    def set(self, valor: str):
        self.var.set(valor)
        self._entry.config(fg=FG_PRIMARY)


# ── Panel de Log ───────────────────────────────────────────────────────────────

class PanelLog(tk.Frame):
    """Panel de texto con scroll y coloreado por tipo de mensaje."""

    def __init__(self, parent, titulo="LOG DE ACTIVIDAD", color_cabecera=None, **kwargs):
        super().__init__(parent, bg=BG_BASE, **kwargs)
        _color = color_cabecera or ACCENT

        # Cabecera
        cabecera = tk.Frame(self, bg=BG_PANEL, pady=5)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text=f"  {titulo}", font=("Consolas", 9, "bold"),
                 bg=BG_PANEL, fg=_color).pack(side="left", padx=8)
        self._btn_limpiar = tk.Label(
            cabecera, text="LIMPIAR  ", font=FONT_UI_SM,
            bg=BG_PANEL, fg=FG_MUTED, cursor="hand2"
        )
        self._btn_limpiar.pack(side="right", padx=4)
        self._btn_limpiar.bind("<Button-1>", lambda e: self.limpiar())
        self._btn_limpiar.bind("<Enter>", lambda e: self._btn_limpiar.config(fg=ACCENT))
        self._btn_limpiar.bind("<Leave>", lambda e: self._btn_limpiar.config(fg=FG_MUTED))

        # Área de texto
        contenedor = tk.Frame(self, bg=BG_BASE, highlightbackground=BORDER,
                              highlightthickness=1)
        contenedor.pack(fill="both", expand=True)

        self._texto = tk.Text(
            contenedor,
            font=FONT_MONO_SM,
            bg=BG_BASE,
            fg=FG_PRIMARY,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            wrap="word",
            spacing1=4,
            spacing3=4,
            state="disabled",
            cursor="arrow",
        )
        scroll_v = tk.Scrollbar(contenedor, orient="vertical",
                                command=self._texto.yview,
                                bg=BG_CARD, troughcolor=BG_BASE,
                                activebackground=ACCENT, relief="flat", bd=0, width=10)
        self._texto.config(yscrollcommand=scroll_v.set)

        scroll_v.pack(side="right", fill="y")
        self._texto.pack(fill="both", expand=True)

        # Configurar tags de color
        for emoji, color in LOG_COLORS.items():
            self._texto.tag_config(emoji, foreground=color)
        self._texto.tag_config("timestamp", foreground=FG_MUTED)
        self._texto.tag_config("separador", foreground=BORDER_ACCENT)
        self._texto.tag_config("resumen", foreground=ACCENT, font=("Consolas", 9, "bold"))
        self._texto.tag_config("sin_clasificar", foreground=RED, background=RED_DIM)
        self._texto.tag_config("sin_clasificar_pct", foreground=ACCENT, background=RED_DIM, font=("Consolas", 8, "bold"))

    # Paleta de colores para nombres de carpeta (HSL bien distribuidos)
    _PALETA = [
        "#e06c75", "#e5c07b", "#98c379", "#56b6c2",
        "#61afef", "#c678dd", "#d19a66", "#be5046",
        "#2bbac5", "#a9d4a0", "#f0a500", "#7f84be",
    ]

    def _color_para_nombre(self, nombre: str) -> str:
        """Devuelve siempre el mismo color para el mismo nombre."""
        idx = hash(nombre.lower()) % len(self._PALETA)
        return self._PALETA[idx]

    def _asegurar_tag_nombre(self, nombre: str):
        """Crea el tag de color para este nombre si no existe."""
        tag = f"nombre_{nombre}"
        try:
            self._texto.tag_cget(tag, "foreground")
        except Exception:
            color = self._color_para_nombre(nombre)
            self._texto.tag_config(tag, foreground=color, font=("Consolas", 8, "bold"))
        return tag

    def agregar_con_nombre(self, mensaje: str, nombre: str):
        """
        Inserta la línea del log resaltando [nombre] con su color propio.
        Busca el patrón [nombre] dentro del mensaje y lo colorea.
        """
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M:%S")
        tag_nombre = self._asegurar_tag_nombre(nombre)
        patron = f"[{nombre}]"

        self._texto.config(state="normal")
        self._texto.insert("end", f"[{hora}] ", "timestamp")

        idx = mensaje.find(patron)
        if idx >= 0:
            self._texto.insert("end", mensaje[:idx], "✅")
            self._texto.insert("end", patron, tag_nombre)
            self._texto.insert("end", mensaje[idx + len(patron):] + "\n", "✅")
        else:
            self._texto.insert("end", mensaje + "\n", "✅")

        self._texto.see("end")
        self._texto.config(state="disabled")

    def _detectar_tag(self, mensaje: str) -> str:
        for emoji in LOG_COLORS:
            if mensaje.startswith(emoji):
                return emoji
        return ""

    def agregar(self, mensaje: str, tag: str | None = None):
        """Añade una línea al log con coloración automática."""
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M:%S")

        self._texto.config(state="normal")
        self._texto.insert("end", f"[{hora}] ", "timestamp")

        t = tag or self._detectar_tag(mensaje)
        if t:
            self._texto.insert("end", mensaje + "\n", t)
        else:
            self._texto.insert("end", mensaje + "\n")

        self._texto.see("end")
        self._texto.config(state="disabled")

    def separador(self):
        self._texto.config(state="normal")
        self._texto.insert("end", "─" * 72 + "\n", "separador")
        self._texto.see("end")
        self._texto.config(state="disabled")

    def resumen(self, texto: str):
        self._texto.config(state="normal")
        self._texto.insert("end", texto + "\n", "resumen")
        self._texto.see("end")
        self._texto.config(state="disabled")

    def agregar_sin_clasificar(self, mensaje: str):
        """Añade línea en rojo; la parte con porcentaje (XX% < YY%) en ámbar."""
        import re
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M:%S")
        self._texto.config(state="normal")
        self._texto.insert("end", f"[{hora}] ", "timestamp")

        # Separar el porcentaje final: "(44% < 72%)"
        m = re.search(r"(\(\d+% [<>] \d+%\))", mensaje)
        if m:
            antes = mensaje[:m.start()]
            pct   = m.group(1)
            resto = mensaje[m.end():]
            self._texto.insert("end", antes, "sin_clasificar")
            self._texto.insert("end", pct, "sin_clasificar_pct")
            self._texto.insert("end", resto + "\n", "sin_clasificar")
        else:
            self._texto.insert("end", mensaje + "\n", "sin_clasificar")

        self._texto.see("end")
        self._texto.config(state="disabled")

    def limpiar(self):
        self._texto.config(state="normal")
        self._texto.delete("1.0", "end")
        self._texto.config(state="disabled")


# ── Barra de progreso custom ───────────────────────────────────────────────────

class BarraProgreso(tk.Frame):
    """Barra de progreso dibujada en Canvas con estilo industrial."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)

        # Etiqueta de estado
        self._lbl_estado = tk.Label(self, text="En espera", font=FONT_UI_SM,
                                    bg=BG_PANEL, fg=FG_SECONDARY, anchor="w")
        self._lbl_estado.pack(fill="x", padx=10, pady=(6, 2))

        # Canvas de la barra
        self._canvas = tk.Canvas(self, height=14, bg=BG_CARD,
                                 highlightthickness=0, relief="flat")
        self._canvas.pack(fill="x", padx=10, pady=(0, 2))

        # Porcentaje
        fila = tk.Frame(self, bg=BG_PANEL)
        fila.pack(fill="x", padx=10, pady=(0, 6))
        self._lbl_pct = tk.Label(fila, text="0%", font=FONT_BADGE,
                                 bg=BG_PANEL, fg=ACCENT, width=5, anchor="w")
        self._lbl_pct.pack(side="left")
        self._lbl_conteo = tk.Label(fila, text="0 / 0 archivos",
                                    font=FONT_UI_SM, bg=BG_PANEL, fg=FG_MUTED, anchor="e")
        self._lbl_conteo.pack(side="right")

        self._valor = 0.0
        self._canvas.bind("<Configure>", self._redibujar)

    def actualizar(self, valor: float, actual: int = 0, total: int = 0, estado: str = ""):
        """valor entre 0.0 y 1.0"""
        self._valor = max(0.0, min(1.0, valor))
        pct = int(self._valor * 100)
        self._lbl_pct.config(text=f"{pct}%")
        if total:
            self._lbl_conteo.config(text=f"{actual} / {total} archivos")
        if estado:
            # Truncar texto largo para que quepa en la etiqueta
            max_chars = 80
            texto = estado if len(estado) <= max_chars else estado[:max_chars] + "…"
            self._lbl_estado.config(text=texto)
        self._redibujar()

    def _redibujar(self, event=None):
        w = self._canvas.winfo_width()
        h = 14
        self._canvas.delete("all")

        # Fondo
        self._canvas.create_rectangle(0, 0, w, h, fill=BG_CARD, outline="")

        # Relleno animado
        fill_w = int(w * self._valor)
        if fill_w > 0:
            # Gradiente simulado con dos rectángulos
            self._canvas.create_rectangle(0, 0, fill_w, h, fill=ACCENT_DARK, outline="")
            self._canvas.create_rectangle(0, 0, fill_w, h // 2,
                                          fill=ACCENT, outline="", stipple="gray50")

        # Borde
        self._canvas.create_rectangle(0, 0, w - 1, h - 1,
                                      outline=BORDER_ACCENT, fill="")

    def reset(self):
        self._valor = 0.0
        self._lbl_pct.config(text="0%")
        self._lbl_conteo.config(text="0 / 0 archivos")
        self._lbl_estado.config(text="En espera")
        self._redibujar()


# ── Badge / etiqueta de stat ───────────────────────────────────────────────────

class BadgeStat(tk.Frame):
    """Muestra un número grande con etiqueta pequeña."""

    def __init__(self, parent, etiqueta, color=FG_PRIMARY, **kwargs):
        super().__init__(parent, bg=BG_CARD, **kwargs)
        self._color = color
        self._var = tk.StringVar(value="0")

        tk.Label(self, textvariable=self._var,
                 font=("Consolas", 22, "bold"),
                 bg=BG_CARD, fg=color).pack(pady=(8, 0))
        tk.Label(self, text=etiqueta.upper(),
                 font=("Segoe UI", 7),
                 bg=BG_CARD, fg=FG_MUTED).pack(pady=(0, 8))

    def set(self, valor: int):
        self._var.set(str(valor))

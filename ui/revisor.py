"""
ui/revisor.py
Ventana de revisión por lotes.
Cuadrícula de tarjetas: imagen grande + OCR + desplegable.
"""
import tkinter as tk
from pathlib import Path
from ui.theme import *

CARPETA_SIN_CLASIFICAR = "_Sin clasificar"
POR_FECHA_LABEL        = "— Por fecha —"
POR_FECHA              = "__POR_FECHA__"

# Tarjetas por fila
COLS = 4
# Tamaño miniatura dentro de la tarjeta
THUMB_W, THUMB_H = 190, 150


class VentanaRevisionLote(tk.Toplevel):

    def __init__(self, parent, items, num_lote: int, total_lotes: int,
                 nombres: list[str], log_colores_fn, on_confirmar, on_cancelar):
        super().__init__(parent)
        self.title(f"Revisión — Lote {num_lote} de {total_lotes}")
        self.configure(bg=BG_BASE)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        self._items        = items
        self._nombres      = nombres
        self._log_color    = log_colores_fn
        self._on_confirmar = on_confirmar
        self._on_cancelar  = on_cancelar
        self._opciones     = nombres + [CARPETA_SIN_CLASIFICAR, POR_FECHA_LABEL]
        self._vars: list[tk.StringVar] = []

        self._construir_ui(num_lote, total_lotes)
        self._centrar()

    def _centrar(self):
        self.update_idletasks()
        self.resizable(False, False)
        w = 960
        h = min(820, self.winfo_screenheight() - 60)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ──────────────────────────────────────────────────────────────────────────

    def _construir_ui(self, num_lote, total_lotes):
        # Cabecera
        cab = tk.Frame(self, bg=BG_PANEL, pady=10)
        cab.pack(fill="x")
        tk.Label(cab, text=f"⏸  REVISIÓN — LOTE {num_lote} DE {total_lotes}",
                 font=("Consolas", 12, "bold"), bg=BG_PANEL, fg=ACCENT).pack(side="left", padx=PAD)
        tk.Label(cab, text=f"{len(self._items)} archivos en este lote",
                 font=("Consolas", 10), bg=BG_PANEL, fg=FG_SECONDARY).pack(side="left")
        tk.Frame(self, bg=BORDER_ACCENT, height=1).pack(fill="x")

        # Cuadrícula directa, sin scroll
        self._grid = tk.Frame(self, bg=BG_BASE)
        self._grid.pack(fill="both", expand=True)

        # Tarjetas en cuadrícula
        for idx, item in enumerate(self._items):
            row, col = divmod(idx, COLS)
            self._tarjeta(self._grid, idx, item, row, col)

        # Barra de botones
        tk.Frame(self, bg=BORDER_ACCENT, height=1).pack(fill="x")
        barra = tk.Frame(self, bg=BG_PANEL, pady=10)
        barra.pack(fill="x", padx=PAD)
        self._boton(barra, "✔  CONFIRMAR Y MOVER ESTE LOTE",
                    self._confirmar, ACCENT, BG_BASE).pack(side="left", padx=(0, 10))
        self._boton(barra, "⛔  CANCELAR TODO",
                    self._cancelar, RED_DIM, RED).pack(side="left")
        tk.Label(barra,
                 text="Cambia el desplegable antes de confirmar.",
                 font=("Segoe UI", 9), bg=BG_PANEL, fg=FG_MUTED).pack(side="right", padx=8)

    # ──────────────────────────────────────────────────────────────────────────

    def _tarjeta(self, parent, idx, item, row, col):
        """Tarjeta: desplegable arriba → imagen → nombre → OCR."""
        bg = BG_CARD
        card = tk.Frame(parent, bg=bg, highlightbackground=BORDER,
                        highlightthickness=1, padx=8, pady=8)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        parent.columnconfigure(col, weight=1)

        # ── Carpeta destino (arriba) ───────────────────────────────────────────
        tk.Label(card, text="CARPETA DESTINO",
                 font=("Consolas", 8, "bold"), bg=bg, fg=ACCENT,
                 anchor="w").pack(fill="x")

        var = tk.StringVar()
        if item.nombre_sugerido in self._nombres:
            var.set(item.nombre_sugerido)
        elif item.nombre_sugerido == CARPETA_SIN_CLASIFICAR:
            var.set(CARPETA_SIN_CLASIFICAR)
        else:
            var.set(POR_FECHA_LABEL)
        self._vars.append(var)

        menu_frame = tk.Frame(card, bg=BG_INPUT,
                              highlightbackground=BORDER, highlightthickness=1)
        menu_frame.pack(fill="x", pady=(2, 8))
        menu = tk.OptionMenu(menu_frame, var, *self._opciones)
        menu.config(bg=BG_INPUT, fg=FG_PRIMARY, font=("Segoe UI", 10),
                    activebackground=BG_HOVER, activeforeground=FG_PRIMARY,
                    highlightthickness=0, relief="flat", bd=0,
                    anchor="w", width=24)
        menu["menu"].config(bg=BG_INPUT, fg=FG_PRIMARY, font=("Segoe UI", 10),
                            activebackground=ACCENT_DIM, activeforeground=ACCENT,
                            relief="flat", bd=0)
        menu.pack(fill="x")

        # ── Imagen ────────────────────────────────────────────────────────────
        img_frame = tk.Frame(card, bg=BG_BASE, width=THUMB_W, height=THUMB_H)
        img_frame.pack_propagate(False)
        img_frame.pack(fill="x", pady=(0, 6))
        lbl_img = tk.Label(img_frame, bg=BG_BASE, text="Cargando…",
                           fg=FG_MUTED, font=("Segoe UI", 10))
        lbl_img.pack(fill="both", expand=True)
        self.after(60 + idx * 40, lambda l=lbl_img, it=item: self._cargar_thumb(l, it))

        # ── Nombre archivo ────────────────────────────────────────────────────
        tk.Label(card, text=item.archivo.name,
                 font=("Consolas", 9), bg=bg, fg=FG_SECONDARY,
                 wraplength=THUMB_W, justify="left", anchor="w").pack(fill="x", pady=(0, 4))

        # ── OCR detectado ─────────────────────────────────────────────────────
        tk.Label(card, text="OCR DETECTADO",
                 font=("Consolas", 8, "bold"), bg=bg, fg=ACCENT,
                 anchor="w").pack(fill="x")
        motivo = item.motivo or "Sin texto OCR detectado"
        ocr_frame = tk.Frame(card, bg=ACCENT_DIM,
                             highlightbackground=ACCENT, highlightthickness=1)
        ocr_frame.pack(fill="x", pady=(2, 0))
        tk.Label(ocr_frame, text=motivo,
                 font=("Consolas", 8), bg=ACCENT_DIM, fg=ACCENT,
                 wraplength=THUMB_W - 12, justify="left",
                 padx=6, pady=5, anchor="w").pack(fill="x")

    # ──────────────────────────────────────────────────────────────────────────

    def _cancelar(self):
        """Cierra la ventana limpiamente antes de llamar al callback."""
        self.grab_release()
        self.destroy()
        self._on_cancelar()

    def _cargar_thumb(self, lbl, item):
        try:
            from PIL import Image, ImageTk
            img = Image.open(item.archivo)
            img.thumbnail((THUMB_W, THUMB_H))
            photo = ImageTk.PhotoImage(img)
            lbl.config(image=photo, text="")
            lbl._img_ref = photo  # evitar GC
        except Exception as e:
            lbl.config(text=f"Sin previsualización\n{e}", fg=FG_MUTED,
                       font=("Segoe UI", 9))

    def _boton(self, parent, texto, comando, bg, fg):
        btn = tk.Label(parent, text=texto, font=("Consolas", 10, "bold"),
                       bg=bg, fg=fg, padx=18, pady=10,
                       cursor="hand2", relief="flat")
        btn.bind("<Button-1>", lambda e: comando())
        btn.bind("<Enter>",  lambda e: btn.config(
            bg=BG_HOVER if bg not in (RED_DIM, ACCENT) else (RED if bg == RED_DIM else ACCENT_DARK)))
        btn.bind("<Leave>",  lambda e: btn.config(bg=bg))
        return btn

    def _confirmar(self):
        for item, var in zip(self._items, self._vars):
            opcion = var.get()
            item.carpeta_elegida = POR_FECHA if opcion == POR_FECHA_LABEL else opcion
        self.grab_release()
        self.destroy()
        self._on_confirmar(self._items)

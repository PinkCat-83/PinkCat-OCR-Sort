"""
ui/app.py
Ventana principal de OrganizadorFotos.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from ui.theme import *
from ui.widgets import BotonAccion, EntradaRuta, PanelLog, BarraProgreso, BadgeStat
from core.worker import TrabajadorOrganizador
from core.nombres_config import cargar_nombres, guardar_nombres, crear_ejemplo
from core.ocr_engine import UMBRAL_SIMILITUD
from core.worker import CANCELAR_TODO, POR_FECHA
from core.config_paths import resolver_ubicacion_sesion, resolver_ubicacion_nombres, guardar_puntero, guardar_json_atomico, leer_json
from ui.revisor import VentanaRevisionLote


class OrganizadorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.withdraw()  # oculto hasta resolver la ubicación de la sesión
        self.title("PinkCat OCR Sort")
        self.geometry("1140x700")
        self.minsize(900, 580)
        self.configure(bg=BG_BASE)
        self._centrar_ventana(1140, 700)

        # Ubicación configurable del sesion.json real (puntero en %APPDATA%,
        # elección obligatoria en el primer uso si no hay puntero válido).
        self._sesion_path = resolver_ubicacion_sesion(self)
        # Ídem para la lista de nombres (nombres.txt): puntero propio,
        # NUNCA la ruta absoluta dentro de sesion.json (que sí viaja
        # sincronizado y podría no coincidir entre ordenadores).
        self._nombres_path = resolver_ubicacion_nombres(self, crear_inicial=crear_ejemplo)
        self.deiconify()

        self._trabajador: TrabajadorOrganizador | None = None
        self._en_proceso = False
        self._nombres: list[str] = []
        self._conteo_carpetas: dict[str, int] = {}  # nombre → archivos enviados
        self._modo_revision = tk.BooleanVar(value=False)

        self._construir_ui()
        self._aplicar_estilo_ttk()
        self._cargar_nombres_inicio()
        self._restaurar_sesion()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _centrar_ventana(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ──────────────────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        self._construir_barra_titulo()
        cuerpo = tk.Frame(self, bg=BG_BASE)
        cuerpo.pack(fill="both", expand=True)

        panel_izq = tk.Frame(cuerpo, bg=BG_PANEL, width=360)
        panel_izq.pack(side="left", fill="y", padx=(0, 1))
        panel_izq.pack_propagate(False)
        self._construir_panel_config(panel_izq)

        panel_der = tk.Frame(cuerpo, bg=BG_BASE)
        panel_der.pack(side="left", fill="both", expand=True)
        self._construir_panel_progreso(panel_der)

    def _construir_barra_titulo(self):
        barra = tk.Frame(self, bg=BG_PANEL, height=42)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        izq = tk.Frame(barra, bg=BG_PANEL)
        izq.pack(side="left", padx=16, pady=8)
        tk.Label(izq, text="▣", font=("Consolas", 14), bg=BG_PANEL, fg=ACCENT).pack(side="left", padx=(0, 8))
        tk.Label(izq, text="PINKCAT OCR SORT", font=("Consolas", 11, "bold"), bg=BG_PANEL, fg=FG_PRIMARY).pack(side="left")
        tk.Label(izq, text="  v1.2", font=FONT_MONO_SM, bg=BG_PANEL, fg=FG_MUTED).pack(side="left")
        tk.Frame(self, bg=BORDER_ACCENT, height=1).pack(fill="x")

    def _construir_panel_config(self, parent):
        pad = {"padx": PAD, "pady": (0, PAD_SM)}

        # ── 01 Carpetas ────────────────────────────────────────────────────────
        self._seccion_titulo(parent, "01  CARPETAS")
        self._entrada_origen = EntradaRuta(parent, "Carpeta origen",
            placeholder="Selecciona la carpeta de fotos…",
            comando_examinar=self._elegir_origen)
        self._entrada_origen.pack(fill="x", **pad)
        self._entrada_destino = EntradaRuta(parent, "Carpeta destino",
            placeholder="Donde se guardarán los archivos…",
            comando_examinar=self._elegir_destino)
        self._entrada_destino.pack(fill="x", **pad)

        self._mismo_destino = tk.BooleanVar(value=False)
        chk = tk.Frame(parent, bg=BG_PANEL)
        chk.pack(fill="x", padx=PAD, pady=(0, PAD))
        tk.Checkbutton(chk, text="Organizar en la misma carpeta origen",
            variable=self._mismo_destino, command=self._toggle_mismo_destino,
            bg=BG_PANEL, fg=FG_SECONDARY, activebackground=BG_PANEL,
            activeforeground=FG_PRIMARY, selectcolor=BG_INPUT,
            font=FONT_UI_SM, relief="flat", bd=0).pack(anchor="w")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD_SM)

        # ── 02 Nombres OCR ─────────────────────────────────────────────────────
        self._seccion_titulo(parent, "02  NOMBRES (OCR FUZZY MATCH)")

        # Ruta del archivo .txt
        fila_txt = tk.Frame(parent, bg=BG_PANEL)
        fila_txt.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._entrada_txt = EntradaRuta(fila_txt, "Archivo de nombres (.txt)",
            placeholder="Selecciona el archivo de nombres…",
            comando_examinar=self._elegir_archivo_nombres)
        self._entrada_txt.pack(side="left", fill="x", expand=True)

        # Botones cargar / crear ejemplo
        botones_txt = tk.Frame(parent, bg=BG_PANEL)
        botones_txt.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._btn_cargar_txt = BotonAccion(botones_txt, "↺  CARGAR",
            comando=self._cargar_nombres_manual, estilo="normal")
        self._btn_cargar_txt.pack(side="left", padx=(0, 4))

        self._btn_crear_ejemplo = BotonAccion(botones_txt, "+ CREAR EJEMPLO",
            comando=self._crear_ejemplo_nombres, estilo="normal")
        self._btn_crear_ejemplo.pack(side="left")

        # Badge con conteo de nombres cargados
        self._lbl_nombres_estado = tk.Label(parent, text="Sin nombres cargados",
            font=FONT_MONO_SM, bg=BG_PANEL, fg=FG_MUTED, anchor="w")
        self._lbl_nombres_estado.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Umbral de similitud
        fila_umbral = tk.Frame(parent, bg=BG_PANEL)
        fila_umbral.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        tk.Label(fila_umbral, text="Umbral similitud:", font=FONT_UI_SM,
            bg=BG_PANEL, fg=FG_SECONDARY).pack(side="left")
        self._lbl_umbral = tk.Label(fila_umbral, text=f"{int(UMBRAL_SIMILITUD*100)}%",
            font=FONT_BADGE, bg=BG_PANEL, fg=ACCENT, width=5)
        self._lbl_umbral.pack(side="right")
        self._umbral_var = tk.IntVar(value=int(UMBRAL_SIMILITUD * 100))
        self._slider_umbral = tk.Scale(parent, from_=40, to=100,
            orient="horizontal", variable=self._umbral_var,
            command=self._actualizar_umbral_label,
            bg=BG_PANEL, fg=FG_SECONDARY, troughcolor=BG_INPUT,
            activebackground=ACCENT, highlightthickness=0,
            sliderrelief="flat", bd=0, showvalue=False)
        self._slider_umbral.pack(fill="x", padx=PAD, pady=(0, 2))

        # Nota explicativa
        tk.Label(parent,
            text="Bajo = más permisivo  ·  Alto = más estricto\n"
                 "Sin match → carpeta '_Sin clasificar'",
            font=("Consolas", 7), bg=BG_PANEL, fg=FG_MUTED,
            justify="left").pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Opciones OCR
        opciones = tk.Frame(parent, bg=BG_PANEL)
        opciones.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._usar_ocr = tk.BooleanVar(value=True)
        tk.Checkbutton(opciones, text="Activar OCR", variable=self._usar_ocr,
            bg=BG_PANEL, fg=FG_SECONDARY, activebackground=BG_PANEL,
            activeforeground=FG_PRIMARY, selectcolor=BG_INPUT,
            font=FONT_UI_SM, relief="flat", bd=0).pack(side="left")
        self._usar_gpu = tk.BooleanVar(value=False)
        tk.Checkbutton(opciones, text="GPU (CUDA)", variable=self._usar_gpu,
            bg=BG_PANEL, fg=FG_SECONDARY, activebackground=BG_PANEL,
            activeforeground=FG_PRIMARY, selectcolor=BG_INPUT,
            font=FONT_UI_SM, relief="flat", bd=0).pack(side="left", padx=(PAD, 0))

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD_SM)

        # ── 03 Acción ──────────────────────────────────────────────────────────
        self._seccion_titulo(parent, "03  ACCIÓN")

        # Modo revisión
        chk_rev = tk.Frame(parent, bg=BG_PANEL)
        chk_rev.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        tk.Checkbutton(chk_rev, text="Modo revisión (uno a uno con previsualización)",
            variable=self._modo_revision,
            bg=BG_PANEL, fg=FG_SECONDARY, activebackground=BG_PANEL,
            activeforeground=FG_PRIMARY, selectcolor=BG_INPUT,
            font=FONT_UI_SM, relief="flat", bd=0).pack(anchor="w")

        btns = tk.Frame(parent, bg=BG_PANEL)
        btns.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._btn_iniciar = BotonAccion(btns, "▶  INICIAR ORGANIZACIÓN",
            comando=self._iniciar, estilo="primario")
        self._btn_iniciar.pack(fill="x", pady=(0, 6))
        self._btn_cancelar = BotonAccion(btns, "⛔  CANCELAR",
            comando=self._cancelar, estilo="peligro")
        self._btn_cancelar.pack(fill="x")
        self._btn_cancelar.habilitar(False)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD)
        tk.Label(parent, text="Nombre: dd-MM-yyyy ; HH.mm.ss.ffff",
            font=("Consolas", 7), bg=BG_PANEL, fg=FG_MUTED).pack(anchor="w", padx=PAD)

    def _construir_panel_progreso(self, parent):
        fila_stats = tk.Frame(parent, bg=BG_BASE)
        fila_stats.pack(fill="x", padx=PAD, pady=PAD)
        for attr, etiqueta, color in [
            ("_stat_ok",       "Procesados", GREEN),
            ("_stat_omitidos", "Omitidos",   FG_SECONDARY),
            ("_stat_errores",  "Errores",    RED),
            ("_stat_total",    "Total",      ACCENT),
        ]:
            badge = BadgeStat(fila_stats, etiqueta, color=color)
            badge.pack(side="left", fill="x", expand=True, padx=(0, 4))
            setattr(self, attr, badge)

        barra_frame = tk.Frame(parent, bg=BG_PANEL,
            highlightbackground=BORDER, highlightthickness=1)
        barra_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._barra = BarraProgreso(barra_frame)
        self._barra.pack(fill="x")

        # Dos logs en paralelo
        logs_frame = tk.Frame(parent, bg=BG_BASE)
        logs_frame.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        self._log = PanelLog(logs_frame, titulo="LOG DE ACTIVIDAD")
        self._log.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self._log_sin_clasificar = PanelLog(
            logs_frame,
            titulo="SIN CLASIFICAR",
            color_cabecera=RED,
        )
        self._log_sin_clasificar.pack(side="left", fill="both", expand=True)

    def _seccion_titulo(self, parent, texto):
        tk.Label(parent, text=texto, font=("Consolas", 8, "bold"),
            bg=BG_PANEL, fg=ACCENT, anchor="w", pady=6).pack(fill="x", padx=PAD)

    # ──────────────────────────────────────────────────────────────────────────
    #  GESTIÓN DE NOMBRES
    # ──────────────────────────────────────────────────────────────────────────

    def _cargar_nombres_inicio(self):
        """Carga la lista de nombres desde la ubicación ya resuelta al
        arrancar (self._nombres_path, vía core.config_paths)."""
        ruta = self._nombres_path
        self._entrada_txt.set(str(ruta))
        if ruta.exists():
            self._nombres = cargar_nombres(ruta)
            self._actualizar_estado_nombres()
        else:
            self._lbl_nombres_estado.config(
                text="Archivo de nombres no encontrado — usa CARGAR o CREAR EJEMPLO",
                fg=ORANGE)

    def _elegir_archivo_nombres(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el archivo de nombres",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos", "*.*")]
        )
        if ruta:
            ruta_p = Path(ruta)
            self._entrada_txt.set(str(ruta_p))
            self._nombres = cargar_nombres(ruta_p)
            self._actualizar_estado_nombres()
            self._nombres_path = ruta_p
            guardar_puntero("ruta_nombres", ruta_p)

    def _cargar_nombres_manual(self):
        ruta_str = self._entrada_txt.get().strip()
        ruta = Path(ruta_str) if ruta_str else self._nombres_path
        if not ruta.exists():
            messagebox.showwarning("No encontrado", f"No se encuentra:\n{ruta}")
            return
        self._nombres = cargar_nombres(ruta)
        self._actualizar_estado_nombres()
        self._log.agregar(f"ℹ Nombres recargados: {len(self._nombres)} entradas", "ℹ")

    def _crear_ejemplo_nombres(self):
        ruta_str = self._entrada_txt.get().strip()
        ruta = Path(ruta_str) if ruta_str else self._nombres_path
        crear_ejemplo(ruta)
        self._entrada_txt.set(str(ruta))
        self._nombres = cargar_nombres(ruta)
        self._actualizar_estado_nombres()
        self._nombres_path = ruta
        guardar_puntero("ruta_nombres", ruta)
        messagebox.showinfo("Creado", f"Archivo de ejemplo creado:\n{ruta.resolve()}\n\nEdítalo con cualquier editor de texto.")

    def _actualizar_estado_nombres(self):
        n = len(self._nombres)
        if n == 0:
            self._lbl_nombres_estado.config(
                text="⚠ Archivo vacío o sin nombres válidos", fg=ORANGE)
        else:
            preview = ", ".join(self._nombres[:4])
            if n > 4:
                preview += f" … (+{n-4})"
            self._lbl_nombres_estado.config(
                text=f"✔ {n} nombres: {preview}", fg=GREEN)

    def _actualizar_umbral_label(self, val=None):
        self._lbl_umbral.config(text=f"{self._umbral_var.get()}%")

    # ──────────────────────────────────────────────────────────────────────────
    #  CARPETAS
    # ──────────────────────────────────────────────────────────────────────────

    def _elegir_origen(self):
        ruta = filedialog.askdirectory(title="Carpeta origen")
        if ruta:
            ruta_abs = str(Path(ruta).resolve())
            self._entrada_origen.set(ruta_abs)
            if self._mismo_destino.get():
                self._entrada_destino.set(ruta_abs)

    def _elegir_destino(self):
        ruta = filedialog.askdirectory(title="Carpeta destino")
        if ruta:
            self._entrada_destino.set(str(Path(ruta).resolve()))

    def _toggle_mismo_destino(self):
        if self._mismo_destino.get():
            origen_str = self._entrada_origen.get().strip()
            origen = Path(origen_str) if origen_str else None
            if origen and origen.is_dir():
                self._entrada_destino.set(str(origen.resolve()))
            else:
                # Sin origen válido aún: se sincronizará al elegirlo con el botón
                self._entrada_destino.set("")

    # ──────────────────────────────────────────────────────────────────────────
    #  PROCESO
    # ──────────────────────────────────────────────────────────────────────────

    def _iniciar(self):
        origen_str = self._entrada_origen.get().strip()
        destino_str = self._entrada_destino.get().strip()

        if not origen_str:
            messagebox.showwarning("Falta origen", "Selecciona una carpeta origen.")
            return
        if not destino_str:
            messagebox.showwarning("Falta destino", "Selecciona una carpeta destino.")
            return

        origen, destino = Path(origen_str), Path(destino_str)
        if not origen.is_dir():
            messagebox.showerror("Error", f"La carpeta origen no existe:\n{origen}")
            return
        destino.mkdir(parents=True, exist_ok=True)

        usar_ocr = self._usar_ocr.get()
        if usar_ocr and not self._nombres:
            if not messagebox.askyesno("Sin nombres",
                "OCR activado pero no hay nombres cargados.\n"
                "Las imágenes irán al sistema de fechas.\n\n¿Continuar igualmente?"):
                return

        # Inyectar umbral al módulo OCR antes de lanzar
        import core.ocr_engine as ocr_mod
        ocr_mod.UMBRAL_SIMILITUD = self._umbral_var.get() / 100.0

        self._en_proceso = True
        self._btn_iniciar.habilitar(False)
        self._btn_cancelar.habilitar(True)
        self._barra.reset()
        self._resetear_stats()
        self._conteo_carpetas = {}
        self._log_sin_clasificar.limpiar()
        self._log.separador()
        self._log.agregar(f"ℹ Origen: {origen}", "ℹ")
        self._log.agregar(f"ℹ Destino: {destino}", "ℹ")
        self._log.agregar(f"ℹ OCR: {'activado' if usar_ocr else 'desactivado'} · "
                          f"Nombres: {len(self._nombres)} · "
                          f"Umbral: {self._umbral_var.get()}%", "ℹ")
        self._log.separador()

        self._destino_actual = destino
        self._trabajador = TrabajadorOrganizador(
            origen=origen,
            destino=destino,
            usar_ocr=usar_ocr,
            usar_gpu=self._usar_gpu.get(),
            nombres=self._nombres,
            modo_revision=self._modo_revision.get(),
            on_progreso=self._cb_progreso,
            on_lote_listo=self._cb_lote_listo,
            on_fin=self._cb_fin,
            on_error=self._cb_error,
        )
        self._trabajador.start()

    def _cancelar(self):
        if self._trabajador:
            self._trabajador.cancelar()
            self._log.agregar("⛔ Cancelando…")

    # ──────────────────────────────────────────────────────────────────────────
    #  CALLBACKS
    # ──────────────────────────────────────────────────────────────────────────

    def _cb_progreso(self, actual, total, mensaje):
        self.after(0, self._actualizar_progreso, actual, total, mensaje)

    def _cb_fin(self, stats):
        self.after(0, self._finalizar, stats)

    def _cb_error(self, error):
        self.after(0, self._mostrar_error, error)

    def _extraer_nombre_carpeta(self, mensaje: str) -> str | None:
        """Detecta si el mensaje tiene [NombrePropio] y lo devuelve."""
        import re
        m = re.search(r"\[([^\]]+)\]", mensaje)
        if m:
            nombre = m.group(1)
            if nombre not in ("sin clasificar",) and nombre in self._nombres:
                return nombre
        return None

    def _cb_lote_listo(self, items, num_lote, total_lotes):
        """El worker pausó con un lote analizado — abrir ventana en hilo principal."""
        self.after(0, self._abrir_lote, items, num_lote, total_lotes)

    def _abrir_lote(self, items, num_lote, total_lotes):
        def on_confirmar(items_confirmados):
            if self._trabajador:
                self._trabajador.confirmar_lote(items_confirmados)

        def on_cancelar():
            if self._trabajador:
                self._trabajador.cancelar_lote()

        VentanaRevisionLote(
            self,
            items=items,
            num_lote=num_lote,
            total_lotes=total_lotes,
            nombres=self._nombres,
            log_colores_fn=self._log._color_para_nombre,
            on_confirmar=on_confirmar,
            on_cancelar=on_cancelar,
        )

    def _actualizar_progreso(self, actual, total, mensaje):
        self._barra.actualizar(actual / total if total else 0, actual, total, mensaje)

        if mensaje.startswith("⚠"):
            # Sin clasificar: rojo en ambos logs
            self._log.agregar_sin_clasificar(mensaje)
            self._log_sin_clasificar.agregar_sin_clasificar(mensaje)
            self._stat_omitidos.set(int(self._stat_omitidos._var.get()) + 1)
            return

        if mensaje.startswith("✅"):
            nombre = self._extraer_nombre_carpeta(mensaje)
            if nombre:
                # Resaltar nombre en color en el log
                self._log.agregar_con_nombre(mensaje, nombre)
                # Contabilizar para el resumen final
                self._conteo_carpetas[nombre] = self._conteo_carpetas.get(nombre, 0) + 1
            else:
                self._log.agregar(mensaje)
            self._stat_ok.set(int(self._stat_ok._var.get()) + 1)
            return

        self._log.agregar(mensaje)
        if mensaje.startswith(("⏭", "➖")):
            self._stat_omitidos.set(int(self._stat_omitidos._var.get()) + 1)
        elif mensaje.startswith("❌"):
            self._stat_errores.set(int(self._stat_errores._var.get()) + 1)

    def _finalizar(self, stats):
        self._en_proceso = False
        self._btn_iniciar.habilitar(True)
        self._btn_cancelar.habilitar(False)
        total, ok = stats.get("total", 0), stats.get("ok", 0)
        omitidos, errores = stats.get("omitidos", 0), stats.get("errores", 0)
        self._stat_total.set(total)
        self._stat_ok.set(ok)
        self._stat_omitidos.set(omitidos)
        self._stat_errores.set(errores)
        self._barra.actualizar(1.0, total, total, "✔ Proceso completado")
        self._log.separador()
        self._log.resumen(f"  ✔ COMPLETADO — Total: {total} · OK: {ok} · Omitidos: {omitidos} · Errores: {errores}")
        self._log.separador()
        if total == 0:
            messagebox.showinfo("Sin archivos", "No se encontraron archivos para procesar.")
        else:
            self._mostrar_resumen(total, ok, omitidos, errores, self._destino_actual)

    def _mostrar_resumen(self, total, ok, omitidos, errores, destino):
        """Ventana emergente con resumen detallado por carpeta."""
        from pathlib import Path as _Path

        try:
            win = tk.Toplevel(self)
            win.title("Resumen del proceso")
            win.configure(bg=BG_BASE)
            win.resizable(True, True)
            win.grab_set()

            # ── Cabecera ──────────────────────────────────────────────────────
            cab = tk.Frame(win, bg=BG_PANEL, pady=10)
            cab.pack(fill="x")
            tk.Label(cab, text="▣  RESUMEN DEL PROCESO",
                     font=("Consolas", 11, "bold"), bg=BG_PANEL, fg=ACCENT).pack(padx=PAD)
            tk.Frame(win, bg=BORDER_ACCENT, height=1).pack(fill="x")

            # ── Stats globales ────────────────────────────────────────────────
            sf = tk.Frame(win, bg=BG_BASE)
            sf.pack(fill="x", padx=PAD, pady=PAD)
            for etiqueta, valor, color in [
                ("Total",      total,    FG_PRIMARY),
                ("Procesados", ok,       GREEN),
                ("Omitidos",   omitidos, FG_SECONDARY),
                ("Errores",    errores,  RED),
            ]:
                col = tk.Frame(sf, bg=BG_CARD, padx=14, pady=8)
                col.pack(side="left", fill="x", expand=True, padx=(0, 4))
                tk.Label(col, text=str(valor), font=("Consolas", 20, "bold"),
                         bg=BG_CARD, fg=color).pack()
                tk.Label(col, text=etiqueta.upper(), font=("Segoe UI", 7),
                         bg=BG_CARD, fg=FG_MUTED).pack()

            tk.Frame(win, bg=BORDER_ACCENT, height=1).pack(fill="x", padx=PAD)

            # ── Lista de carpetas ─────────────────────────────────────────────
            if self._conteo_carpetas:
                tk.Label(win, text="  CARPETAS DE DESTINO",
                         font=("Consolas", 8, "bold"),
                         bg=BG_BASE, fg=ACCENT, anchor="w", pady=8).pack(fill="x", padx=PAD)

                # Área con scroll
                contenedor = tk.Frame(win, bg=BG_BASE)
                contenedor.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

                canvas = tk.Canvas(contenedor, bg=BG_BASE, highlightthickness=0)
                scroll = tk.Scrollbar(contenedor, orient="vertical",
                                      command=canvas.yview,
                                      bg=BG_CARD, width=8, relief="flat", bd=0)
                inner = tk.Frame(canvas, bg=BG_BASE)
                inner.bind("<Configure>",
                           lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=inner, anchor="nw")
                canvas.configure(yscrollcommand=scroll.set)
                scroll.pack(side="right", fill="y")
                canvas.pack(side="left", fill="both", expand=True)

                for fila, (nombre, nuevas) in enumerate(
                    sorted(self._conteo_carpetas.items(), key=lambda x: -x[1])
                ):
                    carpeta_real = _Path(destino) / nombre
                    try:
                        totales = sum(1 for f in carpeta_real.rglob("*") if f.is_file())
                    except Exception:
                        totales = "?"

                    bg = BG_CARD if fila % 2 == 0 else BG_PANEL
                    color = self._log._color_para_nombre(nombre)

                    fila_frame = tk.Frame(inner, bg=bg)
                    fila_frame.pack(fill="x", pady=1)

                    # Bullet de color
                    tk.Label(fila_frame, text="●", font=("Consolas", 10),
                             bg=bg, fg=color, padx=8).pack(side="left")

                    # Nombre
                    tk.Label(fila_frame, text=nombre,
                             font=("Consolas", 9, "bold"),
                             bg=bg, fg=color, anchor="w", width=22).pack(side="left")

                    # Nuevas X
                    tk.Label(fila_frame, text="Nuevas",
                             font=("Segoe UI", 8), bg=bg, fg=FG_MUTED).pack(side="left", padx=(8, 2))
                    tk.Label(fila_frame, text=str(nuevas),
                             font=("Consolas", 9, "bold"), bg=bg, fg=GREEN).pack(side="left")

                    # Totales Y
                    tk.Label(fila_frame, text="  ·  Totales",
                             font=("Segoe UI", 8), bg=bg, fg=FG_MUTED).pack(side="left", padx=(4, 2))
                    tk.Label(fila_frame, text=str(totales),
                             font=("Consolas", 9, "bold"), bg=bg, fg=FG_PRIMARY).pack(side="left")

            else:
                tk.Label(win,
                         text="No se enviaron archivos a carpetas de nombres.",
                         font=("Segoe UI", 9), bg=BG_BASE, fg=FG_MUTED).pack(pady=PAD)

            # ── Botón cerrar ──────────────────────────────────────────────────
            tk.Frame(win, bg=BORDER_ACCENT, height=1).pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
            tk.Button(win, text="  CERRAR  ", font=("Consolas", 9, "bold"),
                      bg=ACCENT, fg=BG_BASE, relief="flat", bd=0,
                      padx=20, pady=8, cursor="hand2",
                      command=win.destroy).pack(pady=PAD)

            # Tamaño y centrado
            win.update_idletasks()
            n_filas = len(self._conteo_carpetas)
            h = min(120 + 42 * n_filas + 120, 620)
            w = 480
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        except Exception as e:
            messagebox.showerror("Error en resumen", str(e))

    def _mostrar_error(self, error):
        self._en_proceso = False
        self._btn_iniciar.habilitar(True)
        self._btn_cancelar.habilitar(False)
        self._log.agregar(f"❌ ERROR FATAL: {error}")
        messagebox.showerror("Error inesperado", error)

    def _resetear_stats(self):
        for attr in ("_stat_ok", "_stat_omitidos", "_stat_errores", "_stat_total"):
            getattr(self, attr).set(0)

    # ──────────────────────────────────────────────────────────────────────────
    #  SESIÓN
    # ──────────────────────────────────────────────────────────────────────────

    # La ruta real vive en self._sesion_path, resuelta en __init__ vía
    # resolver_ubicacion_sesion() (puntero en %APPDATA%, elección
    # obligatoria en el primer uso — ver core/config_paths.py).

    def _guardar_sesion(self):
        datos = {
            "origen":        self._entrada_origen.get().strip(),
            "destino":       self._entrada_destino.get().strip(),
            "mismo_destino": self._mismo_destino.get(),
            "umbral":        self._umbral_var.get(),
            "usar_ocr":      self._usar_ocr.get(),
            "usar_gpu":      self._usar_gpu.get(),
            "modo_revision": self._modo_revision.get(),
        }
        try:
            # Guardado atómico: tmp + os.replace(), para no dejar nunca una
            # versión a medio escribir si el archivo vive en una carpeta
            # sincronizada (Drive, Dropbox…).
            guardar_json_atomico(self._sesion_path, datos)
        except Exception:
            pass

    def _restaurar_sesion(self):
        if not self._sesion_path.exists():
            return
        try:
            datos = leer_json(self._sesion_path)
        except Exception:
            return

        if datos.get("origen"):
            self._entrada_origen.set(datos["origen"])
        if datos.get("destino"):
            self._entrada_destino.set(datos["destino"])
        self._mismo_destino.set(datos.get("mismo_destino", False))

        if datos.get("umbral"):
            self._umbral_var.set(datos["umbral"])
            self._actualizar_umbral_label()
        self._usar_ocr.set(datos.get("usar_ocr", True))
        self._usar_gpu.set(datos.get("usar_gpu", False))
        self._modo_revision.set(datos.get("modo_revision", False))

    def _on_closing(self):
        self._guardar_sesion()
        self.destroy()

    def _aplicar_estilo_ttk(self):
        estilo = tk.ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("TScrollbar", background=BG_CARD, troughcolor=BG_BASE,
            arrowcolor=FG_MUTED, bordercolor=BG_BASE, darkcolor=BG_BASE, lightcolor=BG_BASE)

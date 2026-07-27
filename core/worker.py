"""
core/worker.py
Hilo de trabajo. En modo revisión, analiza en lotes de N y pausa
esperando confirmación antes de mover cada lote.
"""
import threading
from pathlib import Path
from typing import Callable

from core.renamer import procesar_archivo, EXTENSIONES_IGNORADAS
from core.ocr_engine import es_imagen, buscar_nombre, CARPETA_SIN_CLASIFICAR

CANCELAR_TODO = "__CANCELAR_TODO__"
POR_FECHA     = "__POR_FECHA__"
TAMANO_LOTE   = 8


class ItemLote:
    """Representa un archivo analizado pendiente de confirmación."""
    def __init__(self, archivo: Path, nombre_sugerido: str | None, motivo: str):
        self.archivo = archivo
        self.nombre_sugerido = nombre_sugerido
        self.motivo = motivo
        # La carpeta final la elige el usuario en la ventana de revisión
        self.carpeta_elegida: str | None = nombre_sugerido


class TrabajadorOrganizador(threading.Thread):

    def __init__(
        self,
        origen: Path,
        destino: Path,
        usar_ocr: bool,
        usar_gpu: bool,
        nombres: list[str],
        modo_revision: bool,
        on_progreso: Callable,
        on_lote_listo: Callable,   # (lote: list[ItemLote]) → pausa hasta respuesta
        on_fin: Callable,
        on_error: Callable,
    ):
        super().__init__(daemon=True)
        self.origen       = origen
        self.destino      = destino
        self.usar_ocr     = usar_ocr
        self.usar_gpu     = usar_gpu
        self.nombres      = nombres
        self.modo_revision = modo_revision
        self.on_progreso  = on_progreso
        self.on_lote_listo = on_lote_listo
        self.on_fin       = on_fin
        self.on_error     = on_error
        self._cancelado   = threading.Event()
        self._lote_evento = threading.Event()
        self._lote_confirmado: list[ItemLote] | None = None  # None = cancelar

    def cancelar(self):
        self._cancelado.set()
        self._lote_confirmado = None
        self._lote_evento.set()

    def confirmar_lote(self, items: list[ItemLote]):
        """La UI llama aquí con los items (con carpeta_elegida ya actualizada)."""
        self._lote_confirmado = items
        self._lote_evento.set()

    def cancelar_lote(self):
        """La UI cancela todo desde la ventana de revisión."""
        self._lote_confirmado = None
        self._lote_evento.set()

    def run(self):
        try:
            archivos = [
                p for p in self.origen.iterdir()
                if p.is_file() and p.suffix.lower() not in EXTENSIONES_IGNORADAS
            ]

            total = len(archivos)
            if total == 0:
                self.on_fin({"total": 0, "ok": 0, "omitidos": 0, "errores": 0})
                return

            stats = {"total": total, "ok": 0, "omitidos": 0, "errores": 0}

            # Dividir en lotes
            lotes = [archivos[i:i+TAMANO_LOTE]
                     for i in range(0, len(archivos), TAMANO_LOTE)]

            procesados = 0
            for num_lote, lote_archivos in enumerate(lotes):
                if self._cancelado.is_set():
                    break

                # ── Fase 1: analizar OCR el lote ──────────────────────────────
                items = []
                for archivo in lote_archivos:
                    if self._cancelado.is_set():
                        break

                    procesados += 1
                    nombre_carpeta = None
                    motivo_ocr = ""

                    if self.usar_ocr and self.nombres and es_imagen(archivo):
                        self.on_progreso(procesados, total, f"🔍 OCR: {archivo.name}")
                        nombre_carpeta, motivo_ocr = buscar_nombre(
                            archivo, self.nombres, gpu=self.usar_gpu
                        )
                        self.on_progreso(procesados, total, f"   ↳ {motivo_ocr}")
                    else:
                        self.on_progreso(procesados, total, f"📂 Analizado: {archivo.name}")

                    items.append(ItemLote(archivo, nombre_carpeta, motivo_ocr))

                if self._cancelado.is_set():
                    break

                # ── Fase 2: en modo revisión, pausar y esperar confirmación ───
                if self.modo_revision and items:
                    n_total_lotes = len(lotes)
                    self.on_progreso(procesados, total,
                        f"⏸ Lote {num_lote+1}/{n_total_lotes} listo para revisión")
                    self._lote_evento.clear()
                    self._lote_confirmado = None
                    self.on_lote_listo(items, num_lote + 1, n_total_lotes)
                    self._lote_evento.wait()

                    if self._lote_confirmado is None:
                        self.on_progreso(procesados, total, "⛔ Revisión cancelada")
                        break

                    items = self._lote_confirmado

                # ── Fase 3: mover archivos del lote ───────────────────────────
                for item in items:
                    if self._cancelado.is_set():
                        break

                    # Resolver carpeta final
                    carpeta = item.carpeta_elegida
                    if carpeta == POR_FECHA:
                        carpeta = None
                    elif carpeta == CARPETA_SIN_CLASIFICAR:
                        pass  # se pasa tal cual

                    self.on_progreso(procesados, total, f"📂 Moviendo: {item.archivo.name}")
                    try:
                        resultado = procesar_archivo(item.archivo, self.destino, carpeta)
                    except Exception as exc:
                        resultado = {"estado": "error",
                                     "archivo": item.archivo.name,
                                     "motivo": str(exc)}

                    estado = resultado.get("estado", "error")
                    motivo_ocr = item.motivo
                    if estado == "ok":
                        stats["ok"] += 1
                        destino_rel = resultado.get("destino", "?")
                        carp = resultado.get("nombre_ocr")
                        if carp == CARPETA_SIN_CLASIFICAR:
                            razon = f" · {motivo_ocr}" if motivo_ocr else ""
                            msg = f"⚠ {resultado['archivo']} → [sin clasificar]{razon}"
                        elif carp:
                            msg = f"✅ {resultado['archivo']} → [{carp}] {destino_rel}"
                        else:
                            msg = f"✅ {resultado['archivo']} → {destino_rel}"
                    elif estado == "omitido":
                        stats["omitidos"] += 1
                        msg = f"⏭ {resultado['archivo']} (ya correcto)"
                    elif estado == "ignorado":
                        stats["omitidos"] += 1
                        msg = f"➖ {resultado['archivo']} (ignorado)"
                    else:
                        stats["errores"] += 1
                        msg = f"❌ {resultado['archivo']}: {resultado.get('motivo','?')}"

                    self.on_progreso(procesados, total, msg)

            self.on_fin(stats)

        except Exception as exc:
            self.on_error(str(exc))

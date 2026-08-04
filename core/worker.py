"""
core/worker.py
Worker thread. In review mode, analyzes files in batches of N and pauses
waiting for confirmation before moving each batch.
"""
import threading
from pathlib import Path
from typing import Callable

from core.renamer import process_file, IGNORED_EXTENSIONS
from core.ocr_engine import is_image, find_name, UNCLASSIFIED_FOLDER
from core.i18n import tr

BY_DATE      = "__BY_DATE__"
BATCH_SIZE   = 8


class BatchItem:
    """Represents an analyzed file pending confirmation."""
    def __init__(self, file: Path, suggested_name: str | None, reason: str):
        self.file = file
        self.suggested_name = suggested_name
        self.reason = reason
        # The final folder is chosen by the user in the review window
        self.chosen_folder: str | None = suggested_name


class OrganizerWorker(threading.Thread):

    def __init__(
        self,
        source: Path,
        dest: Path,
        use_ocr: bool,
        use_gpu: bool,
        names: list[str],
        review_mode: bool,
        on_progress: Callable,
        on_batch_ready: Callable,   # (batch: list[BatchItem]) -> pauses until a response
        on_finish: Callable,
        on_error: Callable,
    ):
        super().__init__(daemon=True)
        self.source       = source
        self.dest         = dest
        self.use_ocr      = use_ocr
        self.use_gpu      = use_gpu
        self.names        = names
        self.review_mode  = review_mode
        self.on_progress   = on_progress
        self.on_batch_ready = on_batch_ready
        self.on_finish     = on_finish
        self.on_error      = on_error
        self._cancelled    = threading.Event()
        self._batch_event  = threading.Event()
        self._confirmed_batch: list[BatchItem] | None = None  # None = cancel

    def cancel(self):
        self._cancelled.set()
        self._confirmed_batch = None
        self._batch_event.set()

    def confirm_batch(self, items: list[BatchItem]):
        """The UI calls this with the items (chosen_folder already updated)."""
        self._confirmed_batch = items
        self._batch_event.set()

    def cancel_batch(self):
        """The UI cancels everything from the review window."""
        self._confirmed_batch = None
        self._batch_event.set()

    def run(self):
        try:
            files = [
                p for p in self.source.iterdir()
                if p.is_file() and p.suffix.lower() not in IGNORED_EXTENSIONS
            ]

            total = len(files)
            if total == 0:
                self.on_finish({"total": 0, "ok": 0, "skipped": 0, "errors": 0})
                return

            stats = {"total": total, "ok": 0, "skipped": 0, "errors": 0}

            # Split into batches
            batches = [files[i:i + BATCH_SIZE]
                       for i in range(0, len(files), BATCH_SIZE)]

            processed = 0
            for batch_num, batch_files in enumerate(batches):
                if self._cancelled.is_set():
                    break

                # ── Phase 1: run OCR on the batch ─────────────────────────
                items = []
                for file in batch_files:
                    if self._cancelled.is_set():
                        break

                    processed += 1
                    folder_name = None
                    ocr_reason = ""

                    if self.use_ocr and self.names and is_image(file):
                        self.on_progress(processed, total, tr("log_ocr_analyzing", file=file.name))
                        folder_name, ocr_reason = find_name(
                            file, self.names, gpu=self.use_gpu
                        )
                        self.on_progress(processed, total, tr("log_ocr_reason", reason=ocr_reason))
                    else:
                        self.on_progress(processed, total, tr("log_analyzed", file=file.name))

                    items.append(BatchItem(file, folder_name, ocr_reason))

                if self._cancelled.is_set():
                    break

                # ── Phase 2: in review mode, pause and wait for confirmation ──
                if self.review_mode and items:
                    total_batches = len(batches)
                    self.on_progress(processed, total,
                        tr("log_batch_ready", num=batch_num + 1, total=total_batches))
                    self._batch_event.clear()
                    self._confirmed_batch = None
                    self.on_batch_ready(items, batch_num + 1, total_batches)
                    self._batch_event.wait()

                    if self._confirmed_batch is None:
                        self.on_progress(processed, total, tr("log_review_cancelled"))
                        break

                    items = self._confirmed_batch

                # ── Phase 3: move the batch's files ───────────────────────
                for item in items:
                    if self._cancelled.is_set():
                        break

                    # Resolve final folder
                    folder = item.chosen_folder
                    if folder == BY_DATE:
                        folder = None
                    elif folder == UNCLASSIFIED_FOLDER:
                        pass  # passed through as-is

                    self.on_progress(processed, total, tr("log_moving", file=item.file.name))
                    try:
                        result = process_file(item.file, self.dest, folder)
                    except Exception as exc:
                        result = {"status": "error",
                                  "file": item.file.name,
                                  "reason": str(exc)}

                    status = result.get("status", "error")
                    ocr_reason = item.reason
                    if status == "ok":
                        stats["ok"] += 1
                        rel_dest = result.get("destination", "?")
                        folder_used = result.get("ocr_name")
                        if folder_used == UNCLASSIFIED_FOLDER:
                            reason_suffix = f" · {ocr_reason}" if ocr_reason else ""
                            msg = tr("log_unclassified", file=result["file"], reason=reason_suffix)
                        elif folder_used:
                            msg = tr("log_ok_folder", file=result["file"], folder=folder_used, dest=rel_dest)
                        else:
                            msg = tr("log_ok", file=result["file"], dest=rel_dest)
                    elif status == "skipped":
                        stats["skipped"] += 1
                        msg = tr("log_skipped", file=result["file"])
                    elif status == "ignored":
                        stats["skipped"] += 1
                        msg = tr("log_ignored", file=result["file"])
                    else:
                        stats["errors"] += 1
                        msg = tr("log_error", file=result["file"], reason=result.get("reason", "?"))

                    self.on_progress(processed, total, msg)

            self.on_finish(stats)

        except Exception as exc:
            self.on_error(str(exc))

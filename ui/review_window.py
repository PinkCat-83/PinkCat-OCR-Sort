"""
ui/review_window.py
Batch review window.
Card grid: large thumbnail + OCR reason + destination dropdown.
"""
import customtkinter as ctk

from core.i18n import tr
from core.ocr_engine import UNCLASSIFIED_FOLDER
from core.worker import BY_DATE
from ui.theme import (
    BG, PANEL, CARD, BORDER, ACCENT, ACCENT_DIM, TEXT, TEXT_DIM,
    TEXT_MUTED, RADIUS_CARD, RADIUS_BTN, PAD,
)
from ui.widgets import ActionButton

# Cards per row
COLS = 4
# Thumbnail size inside the card
THUMB_W, THUMB_H = 190, 150


class BatchReviewWindow(ctk.CTkToplevel):

    def __init__(self, parent, items, batch_num: int, total_batches: int,
                 names: list[str], on_confirm, on_cancel):
        super().__init__(parent)
        self.title(tr("review_window_title", num=batch_num, total=total_batches))
        self.configure(fg_color=BG)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._items       = items
        self._names       = names
        self._on_confirm  = on_confirm
        self._on_cancel   = on_cancel
        by_date_label = tr("review_by_date")
        self._by_date_label = by_date_label
        self._options     = names + [UNCLASSIFIED_FOLDER, by_date_label]
        self._vars: list[ctk.StringVar] = []

        self._build_ui(batch_num, total_batches)
        self._center()

    def _center(self):
        self.update_idletasks()
        self.resizable(False, False)
        w = 960
        h = min(820, self.winfo_screenheight() - 60)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self, batch_num, total_batches):
        header = ctk.CTkFrame(self, fg_color=PANEL, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=tr("review_header", num=batch_num, total=total_batches),
                     font=("Consolas", 15, "bold"), text_color=ACCENT).pack(side="left", padx=PAD)
        ctk.CTkLabel(header, text=tr("review_file_count", count=len(self._items)),
                     font=("Consolas", 12), text_color=TEXT_DIM).pack(side="left")

        # Grid with scroll, in case a batch doesn't fit on screen
        self._grid = ctk.CTkScrollableFrame(self, fg_color=BG)
        self._grid.pack(fill="both", expand=True)

        for idx, item in enumerate(self._items):
            row, col = divmod(idx, COLS)
            self._card(self._grid, idx, item, row, col)

        # Button bar
        bottom = ctk.CTkFrame(self, fg_color=PANEL)
        bottom.pack(fill="x")
        bar = ctk.CTkFrame(bottom, fg_color=PANEL)
        bar.pack(fill="x", padx=PAD, pady=10)
        ActionButton(
            bar, tr("btn_confirm_batch"), command=self._confirm, style="primary",
            width=280, height=40, font=("Consolas", 13, "bold"),
        ).pack(side="left", padx=(0, 10))
        ActionButton(
            bar, tr("btn_cancel_all"), command=self._cancel, style="danger",
            width=180, height=40, font=("Consolas", 13, "bold"),
        ).pack(side="left")
        ctk.CTkLabel(bar, text=tr("review_hint"), font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(side="right", padx=8)

    # ──────────────────────────────────────────────────────────────────────

    def _card(self, parent, idx, item, row, col):
        """Card layout: dropdown on top -> image -> filename -> OCR reason."""
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS_CARD,
                             border_color=BORDER, border_width=1)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(card, text=tr("review_dest_folder"), font=("Consolas", 10, "bold"),
                     text_color=ACCENT, anchor="w").pack(fill="x", padx=8, pady=(8, 0))

        var = ctk.StringVar()
        if item.suggested_name in self._names:
            var.set(item.suggested_name)
        elif item.suggested_name == UNCLASSIFIED_FOLDER:
            var.set(UNCLASSIFIED_FOLDER)
        else:
            var.set(self._by_date_label)
        self._vars.append(var)

        menu = ctk.CTkOptionMenu(
            card, variable=var, values=self._options,
            fg_color=BG, button_color=ACCENT_DIM, button_hover_color=ACCENT,
            text_color=TEXT, dropdown_fg_color=BG, dropdown_text_color=TEXT,
            dropdown_hover_color=ACCENT_DIM, corner_radius=RADIUS_BTN,
            font=("Segoe UI", 12),
        )
        menu.pack(fill="x", padx=8, pady=(2, 8))

        # ── Image ────────────────────────────────────────────────────────
        img_frame = ctk.CTkFrame(card, fg_color=BG, width=THUMB_W, height=THUMB_H)
        img_frame.pack_propagate(False)
        img_frame.pack(fill="x", padx=8, pady=(0, 6))
        lbl_img = ctk.CTkLabel(img_frame, text=tr("review_loading"),
                                text_color=TEXT_MUTED, font=("Segoe UI", 12))
        lbl_img.pack(fill="both", expand=True)
        self.after(60 + idx * 40, lambda l=lbl_img, it=item: self._load_thumb(l, it))

        # ── File name ────────────────────────────────────────────────────
        ctk.CTkLabel(card, text=item.file.name, font=("Consolas", 11),
                     text_color=TEXT_DIM, wraplength=THUMB_W, justify="left",
                     anchor="w").pack(fill="x", padx=8, pady=(0, 4))

        # ── OCR reason ───────────────────────────────────────────────────
        ctk.CTkLabel(card, text=tr("review_ocr_detected"), font=("Consolas", 10, "bold"),
                     text_color=ACCENT, anchor="w").pack(fill="x", padx=8)
        reason = item.reason or tr("review_no_ocr_text")
        ocr_frame = ctk.CTkFrame(card, fg_color=ACCENT_DIM, border_color=ACCENT,
                                  border_width=1, corner_radius=RADIUS_BTN)
        ocr_frame.pack(fill="x", padx=8, pady=(2, 8))
        ctk.CTkLabel(ocr_frame, text=reason, font=("Consolas", 10), text_color=ACCENT,
                     wraplength=THUMB_W - 12, justify="left").pack(fill="x", padx=6, pady=5)

    # ──────────────────────────────────────────────────────────────────────

    def _cancel(self):
        """Closes the window cleanly before calling the callback."""
        self.grab_release()
        self.destroy()
        self._on_cancel()

    def _load_thumb(self, label, item):
        try:
            from PIL import Image
            img = Image.open(item.file)
            img.thumbnail((THUMB_W, THUMB_H))
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            label.configure(image=photo, text="")
            label._image_ref = photo  # avoid GC
        except Exception as e:
            label.configure(text=tr("review_no_preview", error=e), text_color=TEXT_MUTED,
                             font=("Segoe UI", 11))

    def _confirm(self):
        for item, var in zip(self._items, self._vars):
            choice = var.get()
            item.chosen_folder = BY_DATE if choice == self._by_date_label else choice
        self.grab_release()
        self.destroy()
        self._on_confirm(self._items)

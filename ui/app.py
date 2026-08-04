"""
ui/app.py
Main window of PinkCat OCR Sort.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from ui.theme import (
    BG, PANEL, CARD, BORDER, ACCENT, ACCENT_DIM, TEXT, TEXT_DIM, TEXT_MUTED,
    SUCCESS, DANGER, WARNING, RADIUS_BTN, PAD, PAD_SM, FONT_UI, FONT_UI_SM,
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    ACTIVE_THEME_NAME,
)
from ui.widgets import ActionButton, PathEntry, LogPanel, ProgressPanel, StatBadge
from core.worker import OrganizerWorker
from core.names_config import load_names, create_sample
from core.ocr_engine import SIMILARITY_THRESHOLD
from core.config_paths import (
    resolve_session_location, resolve_names_location,
    save_pointer, save_json_atomic, read_json,
)
from core.i18n import load_translations, tr, set_language, get_language, \
    available_languages, on_language_changed
from ui.review_window import BatchReviewWindow

LANGUAGE_DIR = Path(__file__).resolve().parent.parent / "language"
ICON_DIR = Path(__file__).resolve().parent.parent / "ico"
THEME_KEYS = ("pink", "green", "pro")


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        load_translations(LANGUAGE_DIR / "translations.csv")

        self.withdraw()  # hidden until the session location is resolved
        self.title(tr("app_title"))
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=BG)
        self._set_icon()
        self._center_window(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Configurable location of the real session.json (pointer in
        # %APPDATA%, mandatory choice on first use if there's no pointer).
        self._session_path = resolve_session_location(self)
        # Same for the names list (names.txt): its own pointer, NEVER the
        # absolute path inside session.json (which does travel synced and
        # might not match between computers).
        self._names_path = resolve_names_location(self, create_initial=create_sample)
        self.deiconify()
        # CTk's mainloop() runs a one-time "set dark titlebar color" step on
        # Windows the first time the window is shown, which withdraws and
        # re-shows it based on internal state that's only tracked once
        # mainloop()/update() has run. Since we already withdrew/deiconified
        # manually above (to hide the window during the first-run dialogs),
        # calling update() now marks that bookkeeping as done so mainloop()
        # doesn't redo it later and get the restore step wrong (window stuck
        # withdrawn).
        self.update()

        self._worker: OrganizerWorker | None = None
        self._processing = False
        self._names: list[str] = []
        self._folder_counts: dict[str, int] = {}  # name -> files sent
        self._review_mode_var = tk.BooleanVar(value=False)
        self._theme_var = tk.StringVar(value=ACTIVE_THEME_NAME)

        self._build_menu()
        self._build_ui()
        self._load_names_on_start()
        self._restore_session()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        on_language_changed(self.refresh_language)

    def _set_icon(self):
        ico_path = ICON_DIR / "PinkCat OCR Sort.ico"
        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    def _center_window(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ──────────────────────────────────────────────────────────────────────
    #  Classic top settings menu
    # ──────────────────────────────────────────────────────────────────────

    def _build_menu(self):
        self._menubar = tk.Menu(self, tearoff=0)
        self._settings_menu = tk.Menu(self._menubar, tearoff=0)

        self._language_menu = tk.Menu(self._settings_menu, tearoff=0)
        self._language_var = tk.StringVar(value=get_language())
        for language in available_languages():
            self._language_menu.add_radiobutton(
                label=language, variable=self._language_var, value=language,
                command=lambda l=language: self._change_language(l),
            )
        self._settings_menu.add_cascade(label=tr("menu_language"), menu=self._language_menu)

        self._theme_menu = tk.Menu(self._settings_menu, tearoff=0)
        for theme_key in THEME_KEYS:
            self._theme_menu.add_radiobutton(
                label=tr(f"theme_{theme_key}"), variable=self._theme_var, value=theme_key,
                command=lambda t=theme_key: self._change_theme(t),
            )
        self._settings_menu.add_cascade(label=tr("menu_theme"), menu=self._theme_menu)

        self._menubar.add_cascade(label=tr("menu_settings"), menu=self._settings_menu)
        self.configure(menu=self._menubar)

    def _change_language(self, language: str):
        set_language(language)
        self._save_session()

    def _change_theme(self, theme_key: str):
        self._theme_var.set(theme_key)
        self._save_session()
        messagebox.showinfo(tr("menu_theme"), tr("menu_theme_restart_notice"))

    # ──────────────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_title_bar()
        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True)

        left_panel = ctk.CTkFrame(body, fg_color=PANEL, width=380, corner_radius=0)
        left_panel.pack(side="left", fill="y", padx=(0, 1))
        left_panel.pack_propagate(False)
        self._build_left_panel(left_panel)

        right_panel = ctk.CTkFrame(body, fg_color=BG, corner_radius=0)
        right_panel.pack(side="left", fill="both", expand=True)
        self._build_progress_area(right_panel)

    def _build_title_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL, height=44, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left = ctk.CTkFrame(bar, fg_color=PANEL)
        left.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(left, text="▣", font=("Consolas", 16), text_color=ACCENT).pack(side="left", padx=(0, 8))
        self._title_label = ctk.CTkLabel(left, text=tr("app_title").upper(),
                                          font=("Consolas", 13, "bold"), text_color=TEXT)
        self._title_label.pack(side="left")
        self._version_label = ctk.CTkLabel(left, text=f"  {tr('app_version')}",
                                            font=("Consolas", 10), text_color=TEXT_MUTED)
        self._version_label.pack(side="left")

        # PinkCat mascot logo, top-right of the title bar (Design System §8/§9)
        logo_path = ICON_DIR / "logo.png"
        if logo_path.exists():
            from PIL import Image
            logo_img = Image.open(logo_path)
            logo_ctk_img = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(28, 28))
            ctk.CTkLabel(bar, text="", image=logo_ctk_img).pack(side="right", padx=16)

        ctk.CTkFrame(self, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x")

    def _build_left_panel(self, parent):
        pad = {"padx": PAD, "pady": (0, PAD_SM)}

        # ── 01 Folders ───────────────────────────────────────────────────
        self._section_folders_label = self._section_title(parent, tr("section_folders"))
        self._source_entry = PathEntry(parent, tr("label_source_folder"),
            placeholder=tr("placeholder_source_folder"), browse_command=self._choose_source)
        self._source_entry.pack(fill="x", **pad)
        self._dest_entry = PathEntry(parent, tr("label_dest_folder"),
            placeholder=tr("placeholder_dest_folder"), browse_command=self._choose_dest)
        self._dest_entry.pack(fill="x", **pad)

        self._same_folder_var = tk.BooleanVar(value=False)
        self._same_folder_check = ctk.CTkCheckBox(
            parent, text=tr("check_same_folder"), variable=self._same_folder_var,
            command=self._toggle_same_folder, font=FONT_UI_SM, text_color=TEXT_DIM,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
        )
        self._same_folder_check.pack(anchor="w", padx=PAD, pady=(0, PAD))

        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD_SM)

        # ── 02 OCR names ─────────────────────────────────────────────────
        self._section_names_label = self._section_title(parent, tr("section_names"))

        names_row = ctk.CTkFrame(parent, fg_color=PANEL)
        names_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._names_entry = PathEntry(names_row, tr("label_names_file"),
            placeholder=tr("placeholder_names_file"), browse_command=self._choose_names_file)
        self._names_entry.pack(side="left", fill="x", expand=True)

        names_buttons = ctk.CTkFrame(parent, fg_color=PANEL)
        names_buttons.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._load_names_btn = ActionButton(names_buttons, tr("btn_load"),
            command=self._reload_names, style="normal", width=110)
        self._load_names_btn.pack(side="left", padx=(0, 4))
        self._create_sample_btn = ActionButton(names_buttons, tr("btn_create_sample"),
            command=self._create_sample_names, style="normal", width=150)
        self._create_sample_btn.pack(side="left")

        self._names_status_label = ctk.CTkLabel(parent, text=tr("names_status_none"),
            font=("Consolas", 11), text_color=TEXT_MUTED, anchor="w")
        self._names_status_label.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        threshold_row = ctk.CTkFrame(parent, fg_color=PANEL)
        threshold_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._threshold_caption = ctk.CTkLabel(threshold_row, text=tr("label_threshold"),
            font=FONT_UI_SM, text_color=TEXT_DIM)
        self._threshold_caption.pack(side="left")
        self._threshold_var = tk.IntVar(value=int(SIMILARITY_THRESHOLD * 100))
        self._threshold_label = ctk.CTkLabel(threshold_row, text=f"{self._threshold_var.get()}%",
            font=("Consolas", 13, "bold"), text_color=ACCENT, width=48)
        self._threshold_label.pack(side="right")
        self._threshold_slider = ctk.CTkSlider(
            parent, from_=40, to=100, number_of_steps=60,
            variable=self._threshold_var, command=self._update_threshold_label,
            fg_color=CARD, progress_color=ACCENT_DIM, button_color=ACCENT,
            button_hover_color=ACCENT,
        )
        self._threshold_slider.pack(fill="x", padx=PAD, pady=(0, 2))

        self._threshold_hint_label = ctk.CTkLabel(parent, text=tr("threshold_hint"),
            font=("Consolas", 10), text_color=TEXT_MUTED, justify="left", anchor="w")
        self._threshold_hint_label.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        options_row = ctk.CTkFrame(parent, fg_color=PANEL)
        options_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._use_ocr_var = tk.BooleanVar(value=True)
        self._use_ocr_check = ctk.CTkCheckBox(
            options_row, text=tr("check_enable_ocr"), variable=self._use_ocr_var,
            font=FONT_UI_SM, text_color=TEXT_DIM, fg_color=ACCENT_DIM, hover_color=ACCENT,
        )
        self._use_ocr_check.pack(side="left")
        self._use_gpu_var = tk.BooleanVar(value=False)
        self._use_gpu_check = ctk.CTkCheckBox(
            options_row, text=tr("check_gpu"), variable=self._use_gpu_var,
            font=FONT_UI_SM, text_color=TEXT_DIM, fg_color=ACCENT_DIM, hover_color=ACCENT,
        )
        self._use_gpu_check.pack(side="left", padx=(PAD, 0))

        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD_SM)

        # ── 03 Action ────────────────────────────────────────────────────
        self._section_action_label = self._section_title(parent, tr("section_action"))

        self._review_mode_check = ctk.CTkCheckBox(
            parent, text=tr("check_review_mode"), variable=self._review_mode_var,
            font=FONT_UI_SM, text_color=TEXT_DIM, fg_color=ACCENT_DIM, hover_color=ACCENT,
        )
        self._review_mode_check.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        buttons = ctk.CTkFrame(parent, fg_color=PANEL)
        buttons.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._start_btn = ActionButton(buttons, tr("btn_start"),
            command=self._start, style="primary", height=38)
        self._start_btn.pack(fill="x", pady=(0, 6))
        self._cancel_btn = ActionButton(buttons, tr("btn_cancel"),
            command=self._cancel, style="danger", height=38)
        self._cancel_btn.pack(fill="x")
        self._cancel_btn.set_enabled(False)

        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", padx=PAD, pady=PAD)
        self._filename_hint_label = ctk.CTkLabel(parent, text=tr("filename_format_hint"),
            font=("Consolas", 10), text_color=TEXT_MUTED, anchor="w")
        self._filename_hint_label.pack(anchor="w", padx=PAD)

    def _build_progress_area(self, parent):
        stats_row = ctk.CTkFrame(parent, fg_color=BG)
        stats_row.pack(fill="x", padx=PAD, pady=PAD)
        self._stat_widgets = {}
        for key, label_key, color in [
            ("processed", "stat_processed", SUCCESS),
            ("skipped",   "stat_skipped",   TEXT_DIM),
            ("errors",    "stat_errors",    DANGER),
            ("total",     "stat_total",     ACCENT),
        ]:
            badge = StatBadge(stats_row, tr(label_key), color=color)
            badge.pack(side="left", fill="x", expand=True, padx=(0, 4))
            self._stat_widgets[key] = badge

        self._progress_panel = ProgressPanel(parent, idle_text=tr("status_idle"))
        self._progress_panel.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._progress_panel.set_count_format(tr("status_files_count", current=0, total=0))

        logs_frame = ctk.CTkFrame(parent, fg_color=BG)
        logs_frame.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        self._log_panel = LogPanel(logs_frame, title=tr("log_title_activity"),
                                    on_clear_click=None)
        self._log_panel.set_clear_label_text(tr("btn_clear"))
        self._log_panel.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self._unclassified_log_panel = LogPanel(
            logs_frame, title=tr("log_title_unclassified"), header_color=DANGER)
        self._unclassified_log_panel.set_clear_label_text(tr("btn_clear"))
        self._unclassified_log_panel.pack(side="left", fill="both", expand=True)

    def _section_title(self, parent, text):
        label = ctk.CTkLabel(parent, text=text, font=("Consolas", 11, "bold"),
                              text_color=ACCENT, anchor="w")
        label.pack(fill="x", padx=PAD, pady=(10, 6))
        return label

    # ──────────────────────────────────────────────────────────────────────
    #  Language hot-reload
    # ──────────────────────────────────────────────────────────────────────

    def refresh_language(self):
        self._menubar.entryconfig(0, label=tr("menu_settings"))
        self._settings_menu.entryconfig(0, label=tr("menu_language"))
        self._settings_menu.entryconfig(1, label=tr("menu_theme"))
        for i, theme_key in enumerate(THEME_KEYS):
            self._theme_menu.entryconfig(i, label=tr(f"theme_{theme_key}"))

        self.title(tr("app_title"))
        self._version_label.configure(text=f"  {tr('app_version')}")

        self._section_folders_label.configure(text=tr("section_folders"))
        self._section_names_label.configure(text=tr("section_names"))
        self._section_action_label.configure(text=tr("section_action"))

        self._source_entry.set_label(tr("label_source_folder"))
        self._source_entry.set_placeholder(tr("placeholder_source_folder"))
        self._dest_entry.set_label(tr("label_dest_folder"))
        self._dest_entry.set_placeholder(tr("placeholder_dest_folder"))
        self._same_folder_check.configure(text=tr("check_same_folder"))

        self._names_entry.set_label(tr("label_names_file"))
        self._names_entry.set_placeholder(tr("placeholder_names_file"))
        self._load_names_btn.set_text(tr("btn_load"))
        self._create_sample_btn.set_text(tr("btn_create_sample"))
        self._update_names_status()

        self._threshold_caption.configure(text=tr("label_threshold"))
        self._threshold_hint_label.configure(text=tr("threshold_hint"))
        self._use_ocr_check.configure(text=tr("check_enable_ocr"))
        self._use_gpu_check.configure(text=tr("check_gpu"))
        self._review_mode_check.configure(text=tr("check_review_mode"))

        self._start_btn.set_text(tr("btn_start"))
        self._cancel_btn.set_text(tr("btn_cancel"))
        self._filename_hint_label.configure(text=tr("filename_format_hint"))

        for key, label_key in [("processed", "stat_processed"), ("skipped", "stat_skipped"),
                                ("errors", "stat_errors"), ("total", "stat_total")]:
            self._stat_widgets[key].set_label(tr(label_key))

        self._progress_panel.set_idle_text(tr("status_idle"))
        self._log_panel.set_clear_label_text(tr("btn_clear"))
        self._unclassified_log_panel.set_clear_label_text(tr("btn_clear"))

    # ──────────────────────────────────────────────────────────────────────
    #  NAMES MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────

    def _load_names_on_start(self):
        """Loads the names list from the already-resolved location at
        startup (self._names_path, via core.config_paths)."""
        path = self._names_path
        self._names_entry.set(str(path))
        if path.exists():
            self._names = load_names(path)
            self._update_names_status()
        else:
            self._names_status_label.configure(text=tr("names_status_missing"), text_color=WARNING)

    def _choose_names_file(self):
        path = filedialog.askopenfilename(
            title=tr("file_dialog_names"),
            filetypes=[(tr("file_dialog_filter_text"), "*.txt"), (tr("file_dialog_filter_all"), "*.*")]
        )
        if path:
            path_p = Path(path)
            self._names_entry.set(str(path_p))
            self._names = load_names(path_p)
            self._update_names_status()
            self._names_path = path_p
            save_pointer("names_path", path_p)

    def _reload_names(self):
        path_str = self._names_entry.get().strip()
        path = Path(path_str) if path_str else self._names_path
        if not path.exists():
            messagebox.showwarning(tr("dialog_not_found_title"), tr("dialog_not_found_msg", path=path))
            return
        self._names = load_names(path)
        self._update_names_status()
        self._log_panel.add(tr("log_reloaded", count=len(self._names)), "ℹ")

    def _create_sample_names(self):
        path_str = self._names_entry.get().strip()
        path = Path(path_str) if path_str else self._names_path
        create_sample(path)
        self._names_entry.set(str(path))
        self._names = load_names(path)
        self._update_names_status()
        self._names_path = path
        save_pointer("names_path", path)
        messagebox.showinfo(tr("dialog_created_title"), tr("dialog_created_msg", path=path.resolve()))

    def _update_names_status(self):
        n = len(self._names)
        if n == 0:
            self._names_status_label.configure(text=tr("names_status_empty"), text_color=WARNING)
        else:
            preview = ", ".join(self._names[:4])
            if n > 4:
                preview += f" … (+{n - 4})"
            self._names_status_label.configure(text=tr("names_status_loaded", count=n, preview=preview),
                                                text_color=SUCCESS)

    def _update_threshold_label(self, val=None):
        self._threshold_label.configure(text=f"{int(self._threshold_var.get())}%")

    # ──────────────────────────────────────────────────────────────────────
    #  FOLDERS
    # ──────────────────────────────────────────────────────────────────────

    def _choose_source(self):
        path = filedialog.askdirectory(title=tr("folder_dialog_source"))
        if path:
            abs_path = str(Path(path).resolve())
            self._source_entry.set(abs_path)
            if self._same_folder_var.get():
                self._dest_entry.set(abs_path)

    def _choose_dest(self):
        path = filedialog.askdirectory(title=tr("folder_dialog_dest"))
        if path:
            self._dest_entry.set(str(Path(path).resolve()))

    def _toggle_same_folder(self):
        if self._same_folder_var.get():
            source_str = self._source_entry.get().strip()
            source = Path(source_str) if source_str else None
            if source and source.is_dir():
                self._dest_entry.set(str(source.resolve()))
            else:
                # No valid source yet: will sync once chosen via the button
                self._dest_entry.set("")

    # ──────────────────────────────────────────────────────────────────────
    #  PROCESSING
    # ──────────────────────────────────────────────────────────────────────

    def _start(self):
        source_str = self._source_entry.get().strip()
        dest_str = self._dest_entry.get().strip()

        if not source_str:
            messagebox.showwarning(tr("dialog_source_missing_title"), tr("dialog_source_missing_msg"))
            return
        if not dest_str:
            messagebox.showwarning(tr("dialog_dest_missing_title"), tr("dialog_dest_missing_msg"))
            return

        source, dest = Path(source_str), Path(dest_str)
        if not source.is_dir():
            messagebox.showerror(tr("dialog_error_title"), tr("dialog_source_not_found_msg", path=source))
            return
        dest.mkdir(parents=True, exist_ok=True)

        use_ocr = self._use_ocr_var.get()
        if use_ocr and not self._names:
            if not messagebox.askyesno(tr("dialog_no_names_title"), tr("dialog_no_names_msg")):
                return

        # Inject the threshold into the OCR module before launching
        import core.ocr_engine as ocr_module
        ocr_module.SIMILARITY_THRESHOLD = self._threshold_var.get() / 100.0

        self._processing = True
        self._start_btn.set_enabled(False)
        self._cancel_btn.set_enabled(True)
        self._progress_panel.reset()
        self._reset_stats()
        self._folder_counts = {}
        self._unclassified_log_panel.clear()
        self._log_panel.separator()
        self._log_panel.add(tr("log_source", path=source), "ℹ")
        self._log_panel.add(tr("log_dest", path=dest), "ℹ")
        ocr_state = tr("state_enabled") if use_ocr else tr("state_disabled")
        self._log_panel.add(tr("log_run_config", ocr_state=ocr_state,
                                count=len(self._names), threshold=self._threshold_var.get()), "ℹ")
        self._log_panel.separator()

        self._current_dest = dest
        self._worker = OrganizerWorker(
            source=source,
            dest=dest,
            use_ocr=use_ocr,
            use_gpu=self._use_gpu_var.get(),
            names=self._names,
            review_mode=self._review_mode_var.get(),
            on_progress=self._on_progress_cb,
            on_batch_ready=self._on_batch_ready_cb,
            on_finish=self._on_finish_cb,
            on_error=self._on_error_cb,
        )
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
            self._log_panel.add(tr("log_cancelling"))

    # ──────────────────────────────────────────────────────────────────────
    #  CALLBACKS
    # ──────────────────────────────────────────────────────────────────────

    def _on_progress_cb(self, current, total, message):
        self.after(0, self._update_progress, current, total, message)

    def _on_finish_cb(self, stats):
        self.after(0, self._finish, stats)

    def _on_error_cb(self, error):
        self.after(0, self._show_error, error)

    def _extract_folder_name(self, message: str) -> str | None:
        """Detects if the message has [FolderName] and returns it."""
        import re
        m = re.search(r"\[([^\]]+)\]", message)
        if m:
            name = m.group(1)
            if name in self._names:
                return name
        return None

    def _on_batch_ready_cb(self, items, batch_num, total_batches):
        """The worker paused with an analyzed batch — open the window on the main thread."""
        self.after(0, self._open_batch, items, batch_num, total_batches)

    def _open_batch(self, items, batch_num, total_batches):
        def on_confirm(confirmed_items):
            if self._worker:
                self._worker.confirm_batch(confirmed_items)

        def on_cancel():
            if self._worker:
                self._worker.cancel_batch()

        BatchReviewWindow(
            self,
            items=items,
            batch_num=batch_num,
            total_batches=total_batches,
            names=self._names,
            on_confirm=on_confirm,
            on_cancel=on_cancel,
        )

    def _update_progress(self, current, total, message):
        self._progress_panel.update(current / total if total else 0, current, total, message)
        self._progress_panel.set_count_format(tr("status_files_count", current=current, total=total))

        if message.startswith("⚠"):
            # Unclassified: red in both logs
            self._log_panel.add_unclassified(message)
            self._unclassified_log_panel.add_unclassified(message)
            self._stat_widgets["skipped"].set(self._stat_widgets["skipped"].get() + 1)
            return

        if message.startswith("✅"):
            name = self._extract_folder_name(message)
            if name:
                # Highlight the name in color in the log
                self._log_panel.add_with_name(message, name)
                # Count it for the final summary
                self._folder_counts[name] = self._folder_counts.get(name, 0) + 1
            else:
                self._log_panel.add(message)
            self._stat_widgets["processed"].set(self._stat_widgets["processed"].get() + 1)
            return

        self._log_panel.add(message)
        if message.startswith(("⏭", "➖")):
            self._stat_widgets["skipped"].set(self._stat_widgets["skipped"].get() + 1)
        elif message.startswith("❌"):
            self._stat_widgets["errors"].set(self._stat_widgets["errors"].get() + 1)

    def _finish(self, stats):
        self._processing = False
        self._start_btn.set_enabled(True)
        self._cancel_btn.set_enabled(False)
        total, ok = stats.get("total", 0), stats.get("ok", 0)
        skipped, errors = stats.get("skipped", 0), stats.get("errors", 0)
        self._stat_widgets["total"].set(total)
        self._stat_widgets["processed"].set(ok)
        self._stat_widgets["skipped"].set(skipped)
        self._stat_widgets["errors"].set(errors)
        self._progress_panel.update(1.0, total, total, tr("status_idle"))
        self._log_panel.separator()
        self._log_panel.summary(tr("log_summary_line", total=total, ok=ok, skipped=skipped, errors=errors))
        self._log_panel.separator()
        if total == 0:
            messagebox.showinfo(tr("dialog_no_files_title"), tr("dialog_no_files_msg"))
        else:
            self._show_summary(total, ok, skipped, errors, self._current_dest)

    def _show_summary(self, total, ok, skipped, errors, dest):
        """Popup window with a detailed per-folder summary."""
        try:
            win = ctk.CTkToplevel(self)
            win.title(tr("summary_window_title"))
            win.configure(fg_color=BG)
            win.resizable(True, True)
            win.grab_set()

            header = ctk.CTkFrame(win, fg_color=PANEL)
            header.pack(fill="x")
            ctk.CTkLabel(header, text=tr("summary_header"), font=("Consolas", 14, "bold"),
                         text_color=ACCENT).pack(padx=PAD, pady=10)
            ctk.CTkFrame(win, fg_color=BORDER, height=1).pack(fill="x")

            stats_frame = ctk.CTkFrame(win, fg_color=BG)
            stats_frame.pack(fill="x", padx=PAD, pady=PAD)
            for label_key, value, color in [
                ("stat_total",     total,   TEXT),
                ("stat_processed", ok,      SUCCESS),
                ("stat_skipped",   skipped, TEXT_DIM),
                ("stat_errors",    errors,  DANGER),
            ]:
                col = ctk.CTkFrame(stats_frame, fg_color=CARD)
                col.pack(side="left", fill="x", expand=True, padx=(0, 4))
                ctk.CTkLabel(col, text=str(value), font=("Consolas", 22, "bold"),
                             text_color=color).pack(padx=14, pady=(8, 0))
                ctk.CTkLabel(col, text=tr(label_key).upper(), font=("Segoe UI", 9),
                             text_color=TEXT_MUTED).pack(padx=14, pady=(0, 8))

            ctk.CTkFrame(win, fg_color=BORDER, height=1).pack(fill="x", padx=PAD)

            if self._folder_counts:
                ctk.CTkLabel(win, text=tr("summary_folders_title"), font=("Consolas", 11, "bold"),
                             text_color=ACCENT, anchor="w").pack(fill="x", padx=PAD, pady=(10, 4))

                container = ctk.CTkScrollableFrame(win, fg_color=BG)
                container.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

                for row_i, (name, added) in enumerate(
                    sorted(self._folder_counts.items(), key=lambda x: -x[1])
                ):
                    real_folder = Path(dest) / name
                    try:
                        total_files = sum(1 for f in real_folder.rglob("*") if f.is_file())
                    except Exception:
                        total_files = "?"

                    row_bg = CARD if row_i % 2 == 0 else PANEL
                    color = self._log_panel.name_color(name)

                    row_frame = ctk.CTkFrame(container, fg_color=row_bg)
                    row_frame.pack(fill="x", pady=1)

                    ctk.CTkLabel(row_frame, text="●", font=("Consolas", 12),
                                 text_color=color).pack(side="left", padx=(8, 4))
                    ctk.CTkLabel(row_frame, text=name, font=("Consolas", 11, "bold"),
                                 text_color=color, anchor="w", width=160).pack(side="left")
                    ctk.CTkLabel(row_frame, text=tr("summary_new"), font=("Segoe UI", 10),
                                 text_color=TEXT_MUTED).pack(side="left", padx=(8, 2))
                    ctk.CTkLabel(row_frame, text=str(added), font=("Consolas", 11, "bold"),
                                 text_color=SUCCESS).pack(side="left")
                    ctk.CTkLabel(row_frame, text=f"  ·  {tr('summary_totals')}", font=("Segoe UI", 10),
                                 text_color=TEXT_MUTED).pack(side="left", padx=(4, 2))
                    ctk.CTkLabel(row_frame, text=str(total_files), font=("Consolas", 11, "bold"),
                                 text_color=TEXT).pack(side="left")
            else:
                ctk.CTkLabel(win, text=tr("summary_no_folders"), font=("Segoe UI", 11),
                             text_color=TEXT_MUTED).pack(pady=PAD)

            ctk.CTkFrame(win, fg_color=BORDER, height=1).pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
            ctk.CTkButton(win, text=tr("btn_close"), font=("Consolas", 12, "bold"),
                          fg_color=ACCENT, hover_color=ACCENT_DIM, text_color=BG,
                          corner_radius=RADIUS_BTN, command=win.destroy).pack(pady=PAD)

            win.update_idletasks()
            n_rows = len(self._folder_counts)
            h = min(140 + 40 * n_rows + 140, 620)
            w = 480
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        except Exception as e:
            messagebox.showerror(tr("dialog_error_title"), str(e))

    def _show_error(self, error):
        self._processing = False
        self._start_btn.set_enabled(True)
        self._cancel_btn.set_enabled(False)
        self._log_panel.add(tr("log_fatal_error", error=error))
        messagebox.showerror(tr("dialog_unexpected_error_title"), error)

    def _reset_stats(self):
        for key in ("processed", "skipped", "errors", "total"):
            self._stat_widgets[key].set(0)

    # ──────────────────────────────────────────────────────────────────────
    #  SESSION
    # ──────────────────────────────────────────────────────────────────────

    # The real path lives in self._session_path, resolved in __init__ via
    # resolve_session_location() (pointer in %APPDATA%, mandatory choice on
    # first use — see core/config_paths.py).

    def _save_session(self):
        data = {
            "source":       self._source_entry.get().strip(),
            "destination":  self._dest_entry.get().strip(),
            "same_folder":  self._same_folder_var.get(),
            "threshold":    self._threshold_var.get(),
            "use_ocr":      self._use_ocr_var.get(),
            "use_gpu":      self._use_gpu_var.get(),
            "review_mode":  self._review_mode_var.get(),
            "language":     get_language(),
            "theme":        self._theme_var.get(),
        }
        try:
            # Atomic save: tmp + os.replace(), so a half-written version is
            # never left if the file lives in a synced folder (Drive,
            # Dropbox…).
            save_json_atomic(self._session_path, data)
        except Exception:
            pass

    def _restore_session(self):
        if not self._session_path.exists():
            return
        try:
            data = read_json(self._session_path)
        except Exception:
            return

        if data.get("source"):
            self._source_entry.set(data["source"])
        if data.get("destination"):
            self._dest_entry.set(data["destination"])
        self._same_folder_var.set(data.get("same_folder", False))

        if data.get("threshold"):
            self._threshold_var.set(data["threshold"])
            self._threshold_slider.set(data["threshold"])
            self._update_threshold_label()
        self._use_ocr_var.set(data.get("use_ocr", True))
        self._use_gpu_var.set(data.get("use_gpu", False))
        self._review_mode_var.set(data.get("review_mode", False))

        saved_language = data.get("language")
        if saved_language and saved_language != get_language():
            self._language_var.set(saved_language)
            set_language(saved_language)

    def _on_closing(self):
        self._save_session()
        self.destroy()

"""
ui/widgets.py
Reusable CustomTkinter components, styled from the active PinkCat Design
System theme (ui/theme.py). No literal UI text lives here — every visible
string is passed in by the caller (see ui/app.py / ui/revisor.py), which is
what lets language switching stay a screen-level concern.
"""
from datetime import datetime

import customtkinter as ctk

from ui.theme import (
    BG, PANEL, CARD, CARD_HOVER, BORDER, ACCENT, ACCENT_DIM,
    SUCCESS, DANGER, WARNING, TEXT, TEXT_DIM, TEXT_MUTED,
    RADIUS_BTN, RADIUS_CARD, FONT_UI, FONT_UI_SM, FONT_MONO, FONT_MONO_SM,
    FONT_BADGE, PAD, LOG_COLORS, NAME_PALETTE,
)


def _darken(hex_color: str, amount: float = 0.35) -> str:
    """Returns `hex_color` blended toward black by `amount` (0-1)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c * (1 - amount)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Action button (Add/Edit/Delete state pattern, Design System §7) ───────────

_BUTTON_STYLES = {
    # style: (enabled fg_color, hover_color, text_color)
    "normal":  (PANEL, CARD_HOVER, TEXT),
    "primary": (ACCENT_DIM, ACCENT, TEXT),
    "danger":  (_darken(DANGER), DANGER, "#ffffff"),
    "success": (_darken(SUCCESS), SUCCESS, "#ffffff"),
}


class ActionButton(ctk.CTkButton):
    """Flat action button with the shared enabled/disabled state pattern."""

    def __init__(self, parent, text, command=None, style="normal", width=140, **kwargs):
        fg, hover, fg_text = _BUTTON_STYLES.get(style, _BUTTON_STYLES["normal"])
        self._fg, self._hover, self._fg_text = fg, hover, fg_text
        super().__init__(
            parent, text=text, command=command, width=width,
            fg_color=fg, hover_color=hover, text_color=fg_text,
            text_color_disabled=TEXT_MUTED,
            corner_radius=RADIUS_BTN, font=FONT_UI,
            **kwargs,
        )

    def set_enabled(self, enabled: bool):
        self.configure(state="normal" if enabled else "disabled")

    def set_text(self, text: str):
        self.configure(text=text)


# ── Path entry: label + text field + browse button ─────────────────────────────

class PathEntry(ctk.CTkFrame):
    """Label + text entry + browse button, for folder/file paths."""

    def __init__(self, parent, label, placeholder="", browse_command=None, **kwargs):
        super().__init__(parent, fg_color=PANEL, **kwargs)

        self._label = ctk.CTkLabel(self, text=label.upper(), font=FONT_UI_SM,
                                    text_color=TEXT_DIM, anchor="w")
        self._label.pack(fill="x", pady=(0, 3))

        row = ctk.CTkFrame(self, fg_color=BG, corner_radius=RADIUS_BTN,
                            border_color=BORDER, border_width=1)
        row.pack(fill="x")

        self.var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            row, textvariable=self.var, font=FONT_MONO,
            placeholder_text=placeholder,
            fg_color="transparent", text_color=TEXT,
            border_width=0,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        if browse_command:
            self._browse_btn = ctk.CTkButton(
                row, text="···", width=36, command=browse_command,
                fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=ACCENT,
                corner_radius=RADIUS_BTN, font=("Consolas", 11, "bold"),
            )
            self._browse_btn.pack(side="right", padx=(0, 4), pady=4)

    def set_label(self, text: str):
        self._label.configure(text=text.upper())

    def set_placeholder(self, text: str):
        self._entry.configure(placeholder_text=text)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


# ── Activity log panel ──────────────────────────────────────────────────────────

class LogPanel(ctk.CTkFrame):
    """Scrollable text panel with per-message-type coloring."""

    def __init__(self, parent, title="", header_color=None, on_clear_click=None, **kwargs):
        super().__init__(parent, fg_color=BG, **kwargs)
        color = header_color or ACCENT

        header = ctk.CTkFrame(self, fg_color=PANEL, height=32)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._title_label = ctk.CTkLabel(header, text=f"  {title}", font=("Consolas", 12, "bold"),
                                          text_color=color, anchor="w")
        self._title_label.pack(side="left", padx=8)
        self._clear_label = ctk.CTkLabel(header, text="", font=FONT_UI_SM,
                                          text_color=TEXT_MUTED, cursor="hand2")
        self._clear_label.pack(side="right", padx=4)
        self._clear_label.bind("<Button-1>", lambda e: self._on_clear())
        self._on_clear_click = on_clear_click

        container = ctk.CTkFrame(self, fg_color=BG, border_color=BORDER, border_width=1)
        container.pack(fill="both", expand=True)

        self._text = ctk.CTkTextbox(
            container, font=FONT_MONO_SM, fg_color=BG, text_color=TEXT,
            wrap="word", activate_scrollbars=True, state="disabled",
        )
        self._text.pack(fill="both", expand=True, padx=1, pady=1)

        for emoji, emoji_color in LOG_COLORS.items():
            self._text.tag_config(emoji, foreground=emoji_color)
        self._text.tag_config("timestamp", foreground=TEXT_MUTED)
        self._text.tag_config("separator", foreground=BORDER)
        self._text.tag_config("summary", foreground=ACCENT)
        self._text.tag_config("unclassified", foreground=DANGER)
        self._text.tag_config("unclassified_pct", foreground=ACCENT)

    def set_clear_label_text(self, text: str):
        self._clear_label.configure(text=text)

    def _on_clear(self):
        self.clear()
        if self._on_clear_click:
            self._on_clear_click()

    def name_color(self, name: str) -> str:
        """Always returns the same color for the same detected-name folder."""
        idx = hash(name.lower()) % len(NAME_PALETTE)
        return NAME_PALETTE[idx]

    def _ensure_name_tag(self, name: str):
        tag = f"name_{name}"
        if tag not in self._text.tag_names():
            self._text.tag_config(tag, foreground=self.name_color(name))
        return tag

    def add_with_name(self, message: str, name: str):
        """Inserts the log line highlighting [name] with its own color."""
        hour = datetime.now().strftime("%H:%M:%S")
        name_tag = self._ensure_name_tag(name)
        pattern = f"[{name}]"

        self._text.configure(state="normal")
        self._text.insert("end", f"[{hour}] ", "timestamp")

        idx = message.find(pattern)
        if idx >= 0:
            self._text.insert("end", message[:idx], "✅")
            self._text.insert("end", pattern, name_tag)
            self._text.insert("end", message[idx + len(pattern):] + "\n", "✅")
        else:
            self._text.insert("end", message + "\n", "✅")

        self._text.see("end")
        self._text.configure(state="disabled")

    def _detect_tag(self, message: str) -> str:
        for emoji in LOG_COLORS:
            if message.startswith(emoji):
                return emoji
        return ""

    def add(self, message: str, tag: str | None = None):
        """Adds a line to the log with automatic coloring."""
        hour = datetime.now().strftime("%H:%M:%S")

        self._text.configure(state="normal")
        self._text.insert("end", f"[{hour}] ", "timestamp")

        t = tag or self._detect_tag(message)
        if t:
            self._text.insert("end", message + "\n", t)
        else:
            self._text.insert("end", message + "\n")

        self._text.see("end")
        self._text.configure(state="disabled")

    def separator(self):
        self._text.configure(state="normal")
        self._text.insert("end", "─" * 72 + "\n", "separator")
        self._text.see("end")
        self._text.configure(state="disabled")

    def summary(self, text: str):
        self._text.configure(state="normal")
        self._text.insert("end", text + "\n", "summary")
        self._text.see("end")
        self._text.configure(state="disabled")

    def add_unclassified(self, message: str):
        """Adds a line in red; the percentage part (XX% < YY%) in amber."""
        import re
        hour = datetime.now().strftime("%H:%M:%S")
        self._text.configure(state="normal")
        self._text.insert("end", f"[{hour}] ", "timestamp")

        # Split off the trailing percentage: "(44% < 72%)"
        m = re.search(r"(\(\d+% [<>] \d+%\))", message)
        if m:
            before = message[:m.start()]
            pct    = m.group(1)
            after  = message[m.end():]
            self._text.insert("end", before, "unclassified")
            self._text.insert("end", pct, "unclassified_pct")
            self._text.insert("end", after + "\n", "unclassified")
        else:
            self._text.insert("end", message + "\n", "unclassified")

        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


# ── Progress panel ──────────────────────────────────────────────────────────────

class ProgressPanel(ctk.CTkFrame):
    """Status label + progress bar + percentage/count labels."""

    def __init__(self, parent, idle_text="", **kwargs):
        super().__init__(parent, fg_color=PANEL, **kwargs)
        self._idle_text = idle_text

        self._status_label = ctk.CTkLabel(self, text=idle_text, font=FONT_UI_SM,
                                           text_color=TEXT_DIM, anchor="w")
        self._status_label.pack(fill="x", padx=10, pady=(8, 4))

        self._bar = ctk.CTkProgressBar(self, fg_color=CARD, progress_color=ACCENT,
                                        corner_radius=RADIUS_BTN, height=14)
        self._bar.set(0)
        self._bar.pack(fill="x", padx=10, pady=(0, 4))

        row = ctk.CTkFrame(self, fg_color=PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        self._pct_label = ctk.CTkLabel(row, text="0%", font=FONT_BADGE,
                                        text_color=ACCENT, anchor="w")
        self._pct_label.pack(side="left")
        self._count_label = ctk.CTkLabel(row, text="", font=FONT_UI_SM,
                                          text_color=TEXT_MUTED, anchor="e")
        self._count_label.pack(side="right")

    def set_count_format(self, fmt: str):
        """`fmt` is a template already formatted by the caller (i18n)."""
        self._count_label.configure(text=fmt)

    def update(self, value: float, current: int = 0, total: int = 0, status: str = ""):
        """`value` between 0.0 and 1.0."""
        value = max(0.0, min(1.0, value))
        self._bar.set(value)
        self._pct_label.configure(text=f"{int(value * 100)}%")
        if status:
            max_chars = 90
            text = status if len(status) <= max_chars else status[:max_chars] + "…"
            self._status_label.configure(text=text)

    def reset(self):
        self._bar.set(0)
        self._pct_label.configure(text="0%")
        self._status_label.configure(text=self._idle_text)

    def set_idle_text(self, text: str):
        self._idle_text = text


# ── Stat badge ───────────────────────────────────────────────────────────────────

class StatBadge(ctk.CTkFrame):
    """Big number with a small label underneath."""

    def __init__(self, parent, label, color=TEXT, **kwargs):
        super().__init__(parent, fg_color=CARD, corner_radius=RADIUS_CARD, **kwargs)
        self._var = ctk.StringVar(value="0")

        ctk.CTkLabel(self, textvariable=self._var, font=("Consolas", 24, "bold"),
                     text_color=color).pack(pady=(10, 0))
        self._label_widget = ctk.CTkLabel(self, text=label.upper(), font=("Segoe UI", 10),
                                           text_color=TEXT_MUTED)
        self._label_widget.pack(pady=(0, 10))

    def set_label(self, text: str):
        self._label_widget.configure(text=text.upper())

    def get(self) -> int:
        return int(self._var.get())

    def set(self, value: int):
        self._var.set(str(value))

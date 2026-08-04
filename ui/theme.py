"""
ui/theme.py
Bridges the app to the shared PinkCat Design System (gui/theme_loader.py).
Colors and corner radii come from the active theme dict (get_theme());
typography sizes, padding and window size are this project's own layout
concerns and stay outside the theme, per the Design System (§9).

No UI file should import gui.themes.* directly — only this module calls
get_theme(), reading the active theme name from the externalized session
config (falling back to the shared default when there is no session yet).
"""
from gui.theme_loader import get_theme, DEFAULT_THEME
from core.config_paths import peek_session_settings

ACTIVE_THEME_NAME = peek_session_settings().get("theme", DEFAULT_THEME)
THEME = get_theme(ACTIVE_THEME_NAME)

# ── Design System palette (see gui/themes/*.py for the source values) ──────────
BG          = THEME["bg"]
PANEL       = THEME["panel"]
CARD        = THEME["card"]
CARD_HOVER  = THEME["card_hover"]
BORDER      = THEME["border"]
ACCENT      = THEME["accent"]
ACCENT_DIM  = THEME["accent_dim"]
SUCCESS     = THEME["success"]
DANGER      = THEME["danger"]
WARNING     = THEME["warning"]
INFO        = THEME["info"]
TEXT        = THEME["text"]
TEXT_DIM    = THEME["text_dim"]
TEXT_MUTED  = THEME["text_muted"]
RADIUS_CARD = THEME["corner_radius_card"]
RADIUS_BTN  = THEME["corner_radius_btn"]

# ── Typography (project layout concern, not part of the theme) ────────────────
# Consolas/Segoe UI on Green-Pink, Segoe UI only on Pro (Design System §5).
_MONO_FAMILY = "Consolas" if ACTIVE_THEME_NAME in ("green", "pink") else "Segoe UI"

FONT_MONO    = (_MONO_FAMILY, 9)
FONT_MONO_SM = (_MONO_FAMILY, 8)
FONT_MONO_XS = (_MONO_FAMILY, 7)
FONT_UI      = ("Segoe UI", 12)
FONT_UI_SM   = ("Segoe UI", 11)
FONT_TITLE   = (_MONO_FAMILY, 14, "bold")
FONT_LABEL   = ("Segoe UI", 12)
FONT_BADGE   = (_MONO_FAMILY, 13, "bold")

# ── Measurements (project layout, not part of the theme) ──────────────────────
PAD    = 12
PAD_SM = 6

WINDOW_WIDTH  = 1140
WINDOW_HEIGHT = 700
WINDOW_MIN_WIDTH  = 900
WINDOW_MIN_HEIGHT = 580

# ── Per-message-type log colors ────────────────────────────────────────────────
LOG_COLORS = {
    "✅": SUCCESS,
    "⏭": TEXT_DIM,
    "➖": TEXT_MUTED,
    "❌": DANGER,
    "⚠": DANGER,
    "🔍": INFO,
    "📂": TEXT,
    "⛔": WARNING,
    "ℹ": ACCENT,
    "─": BORDER,
}

# Distinct color palette used to highlight detected-name folders in the log
# and summary window (domain-specific rotating palette, explicitly out of
# scope for the shared Design System — see PinkCat_Design_System.md §11).
NAME_PALETTE = [
    "#e06c75", "#e5c07b", "#98c379", "#56b6c2",
    "#61afef", "#c678dd", "#d19a66", "#be5046",
    "#2bbac5", "#a9d4a0", "#f0a500", "#7f84be",
]

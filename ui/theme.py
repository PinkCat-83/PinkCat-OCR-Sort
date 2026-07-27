"""
ui/theme.py
Paleta de colores y estilos para la interfaz oscura industrial.
"""

# ── Colores base ───────────────────────────────────────────────────────────────
BG_BASE       = "#0f0f0f"   # Negro casi puro — fondo principal
BG_PANEL      = "#161616"   # Paneles elevados
BG_CARD       = "#1e1e1e"   # Cards / secciones
BG_INPUT      = "#252525"   # Entradas de texto
BG_HOVER      = "#2a2a2a"   # Hover sutil

BORDER        = "#2e2e2e"   # Bordes sutiles
BORDER_ACCENT = "#3a3a3a"   # Separadores más visibles

FG_PRIMARY    = "#e8e8e8"   # Texto principal
FG_SECONDARY  = "#888888"   # Texto secundario / labels
FG_MUTED      = "#555555"   # Texto muy atenuado

# ── Colores de acento ──────────────────────────────────────────────────────────
ACCENT        = "#d4a843"   # Ámbar/oro — acento principal
ACCENT_DARK   = "#a07c28"   # Hover del acento
ACCENT_DIM    = "#3d2f0e"   # Fondo tenue del acento

GREEN         = "#4caf7d"   # Éxito / OK
GREEN_DIM     = "#0f2a1c"
ORANGE        = "#e07b39"   # Advertencia
RED           = "#d95f5f"   # Error
RED_DIM       = "#2a0f0f"
BLUE          = "#5b8dd9"   # Info / progreso
BLUE_DIM      = "#0f1e3a"

# ── Tipografía ─────────────────────────────────────────────────────────────────
FONT_MONO    = ("Consolas", 9)
FONT_MONO_SM = ("Consolas", 8)
FONT_UI      = ("Segoe UI", 9)
FONT_UI_SM   = ("Segoe UI", 8)
FONT_TITLE   = ("Segoe UI Semibold", 13)
FONT_LABEL   = ("Segoe UI", 9)
FONT_BADGE   = ("Consolas", 10, "bold")

# ── Medidas ────────────────────────────────────────────────────────────────────
PAD          = 12
PAD_SM       = 6
RADIUS       = 4   # Tk no soporta border-radius nativo, pero lo usamos como referencia

# ── Colores del log por tipo ───────────────────────────────────────────────────
LOG_COLORS = {
    "✅": GREEN,
    "⏭": FG_SECONDARY,
    "➖": FG_MUTED,
    "❌": RED,
    "⚠": RED,
    "🔍": BLUE,
    "📂": FG_PRIMARY,
    "⛔": ORANGE,
    "ℹ": ACCENT,
    "─": BORDER_ACCENT,
}

"""
gui/styles.py
<<<<<<< HEAD
Dark-theme style definitions for the Petrus Onboarding Tool.
=======
Bright-theme style definitions for the Petrus Onboarding Tool.
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
"""

import tkinter as tk
from tkinter import ttk

# ── Color Palette ──────────────────────────────────────────────────────────────
<<<<<<< HEAD
C = {
<<<<<<< HEAD
    "bg":          "#0D1117",   # Deep dark background
    "surface":     "#161B22",   # Card / panel surface
    "surface2":    "#1C2128",   # Secondary surface
    "border":      "#30363D",   # Borders
    "accent":      "#2F81F7",   # Primary blue
    "accent_h":    "#1A6AE8",   # Accent hover
    "accent_dim":  "#1A3A5C",   # Light accent fill
    "success":     "#3FB950",   # Green
    "error":       "#F85149",   # Red
    "warning":     "#D29922",   # Amber
    "text":        "#E6EDF3",   # Primary text
    "text_muted":  "#7D8590",   # Secondary text
    "text_dim":    "#484F58",   # Dimmed text
    "input_bg":    "#10161E",   # Input background
    "highlight":   "#264F78",   # Selection highlight
=======
=======
# ── Color Palettes ────────────────────────────────────────────────────────────
LIGHT = {
>>>>>>> dev
    "bg":          "#F0F4F8",   # Light grey-blue background
    "surface":     "#FFFFFF",   # Card / panel surface (white)
    "surface2":    "#E8EDF2",   # Secondary surface (slightly darker)
    "border":      "#CBD5E1",   # Borders
    "accent":      "#2563EB",   # Primary blue (vivid)
    "accent_h":    "#1D4ED8",   # Accent hover (deeper blue)
    "accent_dim":  "#DBEAFE",   # Light accent fill
    "success":     "#16A34A",   # Green
    "error":       "#DC2626",   # Red
    "warning":     "#D97706",   # Amber
    "text":        "#1E293B",   # Primary text (dark slate)
    "text_muted":  "#64748B",   # Secondary text
    "text_dim":    "#94A3B8",   # Dimmed text
    "input_bg":    "#F8FAFC",   # Input background (very light)
    "highlight":   "#BFDBFE",   # Selection highlight
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
}

DARK = {
    "bg":          "#0F172A",   # Very dark navy
    "surface":     "#1E293B",   # Dark slate surface
    "surface2":    "#334155",   # Slightly lighter slate
    "border":      "#475569",   # Darker borders
    "accent":      "#3B82F6",   # Bright blue
    "accent_h":    "#60A5FA",   # Lighter blue hover
    "accent_dim":  "#1E3A8A",   # Deep navy accent fill
    "success":     "#22C55E",   # Bright green
    "error":       "#EF4444",   # Bright red
    "warning":     "#F59E0B",   # Orange/Amber
    "text":        "#F8FAFC",   # Near-white text
    "text_muted":  "#94A3B8",   # Slate grey text
    "text_dim":    "#64748B",   # Darker grey text
    "input_bg":    "#0F172A",   # Background-colored inputs
    "highlight":   "#3B82F6",   # Selection highlight
}

# Current theme reference (updated via apply_theme)
C = LIGHT.copy()

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"

F = {
    "title_lg": (FONT_FAMILY, 16, "bold"),
    "title":    (FONT_FAMILY, 13, "bold"),
    "subtitle": (FONT_FAMILY, 11, "bold"),
    "subtitle_sm": (FONT_FAMILY, 9, "bold"),
    "body":     (FONT_FAMILY, 10),
    "body_sm":  (FONT_FAMILY, 9),
    "label":    (FONT_FAMILY, 9),
    "mono":     ("Consolas",  9),
    "status":   (FONT_FAMILY,  9),
}


<<<<<<< HEAD
def apply_theme(root: tk.Tk) -> None:
<<<<<<< HEAD
    """Apply dark theme to all ttk widgets."""
=======
    """Apply bright theme to all ttk widgets."""
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
=======
def apply_theme(root: tk.Tk, is_dark: bool = False) -> None:
    """Apply theme to all ttk widgets."""
    global C
    C.update(DARK if is_dark else LIGHT)
    
>>>>>>> dev
    s = ttk.Style(root)
    s.theme_use("clam")

    # -- Base --
    s.configure(".",
        background=C["bg"], foreground=C["text"],
        fieldbackground=C["input_bg"], borderwidth=1,
        relief="flat", font=F["body"],
        troughcolor=C["surface2"], arrowcolor=C["text_muted"],
    )

    # -- TFrame --
    s.configure("TFrame", background=C["bg"])
    s.configure("Card.TFrame", background=C["surface"])
    s.configure("Bar.TFrame",  background=C["surface2"])

    # -- TLabel --
    s.configure("TLabel",        background=C["bg"],       foreground=C["text"])
    s.configure("Card.TLabel",   background=C["surface"],  foreground=C["text"])
    s.configure("Muted.TLabel",  background=C["bg"],       foreground=C["text_muted"], font=F["body_sm"])
    s.configure("Error.TLabel",  background=C["bg"],       foreground=C["error"],      font=F["body_sm"])
    s.configure("Success.TLabel",background=C["bg"],       foreground=C["success"],    font=F["body_sm"])
    s.configure("Dim.TLabel",    background=C["surface"],  foreground=C["text_dim"],   font=F["body_sm"])

    # -- TEntry --
    s.configure("TEntry",
        fieldbackground=C["input_bg"], foreground=C["text"],
        insertcolor=C["text"], borderwidth=1, relief="solid",
        padding=(6, 4),
    )
    s.map("TEntry", fieldbackground=[("readonly", C["surface2"])])

    # -- TCombobox --
    s.configure("TCombobox",
        fieldbackground=C["input_bg"], background=C["surface"],
        foreground=C["text"], arrowcolor=C["text_muted"],
        borderwidth=1, padding=(6, 4),
    )
    s.map("TCombobox",
        fieldbackground=[("readonly", C["surface2"])],
        foreground=[("readonly", C["text"])],
    )

    # -- TButton --
    s.configure("TButton",
        background=C["accent"], foreground="#FFFFFF",
        font=F["body"], borderwidth=0, relief="flat", padding=(14, 8),
    )
    s.map("TButton",
        background=[("active", C["accent_h"]), ("disabled", C["border"])],
        foreground=[("disabled", C["text_muted"])],
    )

    s.configure("Secondary.TButton",
        background=C["surface2"], foreground=C["text"],
        borderwidth=1, relief="solid", padding=(10, 6),
    )
    s.map("Secondary.TButton",
        background=[("active", C["border"])],
    )

    s.configure("Danger.TButton",
        background=C["error"], foreground="#FFFFFF",
        borderwidth=0, relief="flat", padding=(10, 6),
    )

    # -- TCheckbutton --
    s.configure("TCheckbutton", background=C["bg"], foreground=C["text"])
    s.configure("Card.TCheckbutton", background=C["surface"], foreground=C["text"])

    # -- TScrollbar --
    s.configure("TScrollbar",
<<<<<<< HEAD
        background=C["surface"], troughcolor=C["bg"],
=======
        background=C["surface2"], troughcolor=C["bg"],
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
        arrowcolor=C["text_muted"], borderwidth=0, width=10,
    )

    # -- TProgressbar --
    s.configure("TProgressbar",
        background=C["accent"], troughcolor=C["surface2"],
        borderwidth=0, thickness=6,
    )

    # -- TLabelframe --
    s.configure("TLabelframe",
        background=C["surface"], bordercolor=C["border"],
        relief="solid", borderwidth=1,
    )
    s.configure("TLabelframe.Label",
        background=C["surface"], foreground=C["accent"],
        font=F["subtitle"],
    )

    root.configure(bg=C["bg"])

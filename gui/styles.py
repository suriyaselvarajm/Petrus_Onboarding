"""
gui/styles.py
Color palettes and styling definitions for the Petrus Onboarding Tool.
Supports dynamic switching between Light and Dark modes.
"""

import tkinter as tk
from tkinter import ttk

# ── Color Palettes ────────────────────────────────────────────────────────────
LIGHT = {
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
}

DARK = {
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
}

# Current theme reference (updated via apply_theme)
C = DARK.copy()  # Default to dark

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

def apply_theme(root: tk.Tk, is_dark: bool = True) -> None:
    """Apply the chosen theme to all ttk widgets."""
    global C
    C.update(DARK if is_dark else LIGHT)
    
    style = ttk.Style(root)
    # Use 'clam' as base for better customizability
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Common Styles
    style.configure("TFrame", background=C["bg"])
    style.configure("Surface.TFrame", background=C["surface"])
    style.configure("Card.TFrame", background=C["surface"], relief="flat")
    
    # Notebook
    style.configure("TNotebook", background=C["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=C["surface2"], foreground=C["text_muted"], padding=[15, 5], font=F["body_sm"])
    style.map("TNotebook.Tab", 
              background=[("selected", C["surface"])],
              foreground=[("selected", C["accent"])])

    # Labels
    style.configure("TLabel", background=C["bg"], foreground=C["text"], font=F["body"])
    style.configure("Title.TLabel", font=F["title"], foreground=C["text"])
    style.configure("Subtitle.TLabel", font=F["subtitle"], foreground=C["accent"])
    style.configure("Muted.TLabel", foreground=C["text_muted"], font=F["body_sm"])

    # Buttons
    style.configure("TButton", font=F["body_sm"], padding=[12, 6])
    
    # Primary Button (Accent)
    style.configure("Primary.TButton", 
                    background=C["accent"], 
                    foreground="#FFFFFF",
                    borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", C["accent_h"]), ("disabled", C["surface2"])])

    # Secondary Button
    style.configure("Secondary.TButton", 
                    background=C["surface2"], 
                    foreground=C["text"],
                    borderwidth=0)
    style.map("Secondary.TButton",
              background=[("active", C["border"])])

    # Destructive Button
    style.configure("Danger.TButton", 
                    background=C["error"], 
                    foreground="#FFFFFF",
                    borderwidth=0)
    style.map("Danger.TButton",
              background=[("active", "#C53030")])

    # Entry
    style.configure("TEntry", 
                    fieldbackground=C["input_bg"],
                    foreground=C["text"],
                    insertcolor=C["text"],
                    borderwidth=1,
                    relief="solid")

    # Checkbutton
    style.configure("TCheckbutton", 
                    background=C["surface"], 
                    foreground=C["text"],
                    font=F["body_sm"])

    # Treeview (if used)
    style.configure("Treeview",
                    background=C["surface"],
                    foreground=C["text"],
                    fieldbackground=C["surface"],
                    font=F["body_sm"],
                    rowheight=28)
    style.map("Treeview", background=[("selected", C["accent"])])

    # Scrollbar
    style.configure("TScrollbar", 
                    gripcount=0,
                    background=C["surface2"], 
                    darkcolor=C["surface2"], 
                    lightcolor=C["surface2"],
                    troughcolor=C["bg"], 
                    bordercolor=C["bg"], 
                    arrowcolor=C["text_muted"])

    # Update root background
    root.configure(bg=C["bg"])

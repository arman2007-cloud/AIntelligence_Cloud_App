"""
==============================================================================
VISUAL COMPONENTS ENGINE (ui_widgets.py)
==============================================================================
Architecture:
    OOP Encapsulation. Extends 'CustomTkinter' classes to create modular,
    reusable UI elements (DRY principle), keeping main.py declarative.
==============================================================================
"""

import customtkinter as ctk
from config import *

class AccentCard(ctk.CTkFrame):
    """High-level container with a colored lateral accent line."""
    def __init__(self, parent, accent_color=CYAN, **kwargs):
        super().__init__(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        accent = ctk.CTkFrame(self, width=4, corner_radius=2, fg_color=accent_color)
        accent.grid(row=0, column=0, sticky="ns", padx=(12, 0), pady=16)

        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.grid(row=0, column=1, sticky="nsew", padx=(12, 20), pady=12)
        self.inner.grid_columnconfigure(0, weight=1)

class PillNavButton(ctk.CTkButton):
    """Modern Pill-shaped navigation button for the sidebar."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, anchor="w", font=F_UI_B, fg_color="transparent",
                         hover_color=CARD, text_color=TEXT_DIM, corner_radius=10, height=46, **kwargs)

class StatWidget(ctk.CTkFrame):
    """Real-time KPI Dashboard Widget."""
    def __init__(self, parent, label, color, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.lbl_num = ctk.CTkLabel(self, text="0", font=F_STAT_NUM, text_color=color)
        self.lbl_num.pack(anchor="center")
        ctk.CTkLabel(self, text=label, font=F_STAT_LBL, text_color=TEXT_DIM).pack(anchor="center")

    def set_value(self, v):
        self.lbl_num.configure(text=str(v))

class GlowProgressBar(ctk.CTkFrame):
    """Asynchronous Progress Bar with built-in text labels."""
    def __init__(self, parent, color=CYAN, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        track = ctk.CTkFrame(self, height=6, corner_radius=3, fg_color=BORDER)
        track.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        track.grid_columnconfigure(0, weight=1)

        self._bar = ctk.CTkProgressBar(track, height=6, corner_radius=3, fg_color=BORDER, progress_color=color)
        self._bar.grid(row=0, column=0, sticky="ew")
        self._bar.set(0)

        self._lbl = ctk.CTkLabel(self, text="Waiting...", font=F_SUBTITLE, text_color=TEXT_DIM, anchor="w")
        self._lbl.grid(row=1, column=0, sticky="w")

    def update(self, value, text):
        self._bar.set(value)
        self._lbl.configure(text=text)

class PremiumInput(ctk.CTkEntry):
    """Standardized text entry box."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=44, font=F_UI, fg_color=BG, border_color=BORDER_LT,
                         border_width=1, text_color=TEXT, placeholder_text_color=TEXT_GHOST,
                         corner_radius=10, **kwargs)

class PremiumCombo(ctk.CTkComboBox):
    """Standardized Dropdown Menu."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=44, font=F_UI, fg_color=BG, border_color=BORDER_LT,
                         border_width=1, text_color=TEXT, button_color=BORDER_LT,
                         button_hover_color=CYAN, dropdown_fg_color=CARD,
                         dropdown_text_color=TEXT, dropdown_hover_color=BORDER_LT,
                         corner_radius=10, **kwargs)
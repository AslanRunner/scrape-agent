"""
ScrapeAgent - Modern Neumorphic Desktop Application.
Crafted with CustomTkinter featuring a dual-font system (Gotham Display + Segoe UI Body),
high-contrast tactile cards, sunken input fields, seamless dark scrollbars,
zero emojis, and zero-terminal execution.
"""
import os
import sys
import threading
import time
from datetime import datetime
from urllib.parse import urlparse

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent import is_valid_url, normalize_url, derive_default_filename, check_bot_protection
from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.extractor import UniversalExtractor
from core.exporter import export_data
from config import DEFAULT_OUTPUT_DIR

# -----------------------------------------------------------------------------
# WARM AMBER / OBSIDIAN & CREAM DUAL THEME PALETTE
# -----------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#121214",            # Deep warm espresso charcoal
        "card_bg": "#1a1a1f",       # Warm slate/espresso surface
        "card_border": "#2c2c36",   # Subtle warm border
        "card_shadow": "#09090b",   # Deep bottom shadow
        "inset_bg": "#151518",      # Sunken input background
        "inset_border": "#282832",  # Inner recess stroke
        "btn_raised": "#24242c",    # Tactile raised button
        "btn_hover": "#32323c",     # Button hover state
        "btn_border": "#3c3c4a",    # Button highlight rim
        "accent": "#f59e0b",        # Luminous warm amber / gold
        "accent_hover": "#d97706",  # Deep amber hover
        "accent_text": "#18181b",   # High-contrast text on accent
        "accent_card": "#f59e0b",   # Primary CTA button
        "text": "#fafafa",          # Crisp white for clear readability
        "text_subtle": "#d4d4d8",   # Light slate for secondary text
        "muted": "#a1a1aa",         # Crisp neutral labels
        "dim": "#71717a",           # Subdued hints / placeholder
        "success": "#10b981",       # Emerald green dot
        "warning": "#f59e0b",       # Amber warning
        "error": "#ef4444",         # Rose red
        "tree_bg": "#1a1a1f",       # Table background
        "tree_fg": "#fafafa",       # Table row text
        "tree_head_bg": "#24242c",  # Table header background
        "tree_head_fg": "#fafafa",  # Table header text
        "tree_selected": "#2e2e3a", # Table row selected background
    },
    "light": {
        "bg": "#f6f5f0",            # Warm ivory / light canvas
        "card_bg": "#ffffff",       # Pure white card surface
        "card_border": "#e3ded5",   # Soft warm card border
        "card_shadow": "#ded9ce",   # Soft card shadow
        "inset_bg": "#f0ede5",      # Sunken input background
        "inset_border": "#d8d3c5",  # Inset stroke
        "btn_raised": "#eae6dc",    # Tactile raised button
        "btn_hover": "#dfdad0",     # Button hover state
        "btn_border": "#cec8bc",    # Button highlight rim
        "accent": "#d97706",        # Rich warm amber / ochre
        "accent_hover": "#b45309",  # Deep amber hover
        "accent_text": "#ffffff",   # Crisp white text on amber
        "accent_card": "#d97706",   # Primary CTA button
        "text": "#1c1917",          # Deep warm espresso text
        "text_subtle": "#44403c",   # Secondary body text
        "muted": "#78716c",         # Crisp neutral labels
        "dim": "#a8a29e",           # Subdued hints / placeholder
        "success": "#059669",       # Forest green dot
        "warning": "#d97706",       # Amber warning
        "error": "#dc2626",         # Rose red
        "tree_bg": "#ffffff",       # Table background
        "tree_fg": "#1c1917",       # Table row text
        "tree_head_bg": "#eae6dc",  # Table header background
        "tree_head_fg": "#1c1917",  # Table header text
        "tree_selected": "#e3ded5", # Table row selected background
    },
}
NEU = THEMES["dark"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# -----------------------------------------------------------------------------
# DUAL-FONT TYPOGRAPHY ARCHITECTURE
# -----------------------------------------------------------------------------
def resolve_font_pairing():
    """
    Establish a balanced 2-font system:
    1. Display Font (Gotham / Century Gothic) for headers, brand, and prominent badges.
    2. Body Font (Segoe UI) for data tables, form inputs, status labels, and fine metrics.
    """
    display_font = "Century Gothic"
    try:
        import tkinter.font as tkfont
        root = tk.Tk()
        root.withdraw()
        avail = tkfont.families()
        root.destroy()
        for cand in ["Gotham", "Gotham Medium", "Gotham Bold", "Gotham-Book", "Century Gothic"]:
            if cand in avail:
                display_font = cand
                break
    except Exception:
        pass

    return display_font, "Segoe UI"


FONT_DISPLAY, FONT_BODY = resolve_font_pairing()


class ScrapeAgentApp(ctk.CTk):
    """Neumorphic Desktop Application for ScrapeAgent with Dark & Light Warm Amber Theme."""

    def __init__(self):
        super().__init__()

        self.current_theme_name = "dark"
        self.theme = THEMES["dark"]

        self.title("ScrapeAgent · Autonomous Data Extraction")
        self.geometry("1160x800")
        self.minsize(920, 620)
        self.configure(fg_color=self.theme["bg"])

        # Window Icon
        ico_file = os.path.join(PROJECT_ROOT, "assets", "scrape_agent.ico")
        if os.path.exists(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        self.current_records = []
        self.active_cols = []
        self.is_scraping = False

        self._init_ttk_styles()
        self._init_ui()

    def _init_ttk_styles(self):
        """Configure native table with high-legibility body font and seamless aesthetics."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=self.theme["tree_bg"],
            foreground=self.theme["tree_fg"],
            fieldbackground=self.theme["tree_bg"],
            rowheight=32,
            font=(FONT_BODY, 10),
            borderwidth=0,
            highlightthickness=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.theme["tree_head_bg"],
            foreground=self.theme["tree_head_fg"],
            font=(FONT_BODY, 9, "bold"),
            relief="flat",
            padding=8,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", self.theme["tree_selected"])],
            foreground=[("selected", self.theme["accent"])],
        )

    def _init_ui(self):
        t = self.theme

        # 1. TOP HEADER / MASTHEAD (Raised Neumorphic Card)
        self.header_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=16,
            height=70,
        )
        self.header_card.pack(fill="x", padx=20, pady=(16, 12))
        self.header_card.pack_propagate(False)

        # Brand Title Left (Display Font)
        title_box = ctk.CTkFrame(self.header_card, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="ScrapeAgent",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=21, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_title.pack(anchor="w")

        # Subtitle (Body Font, High Legibility)
        self.lbl_sub = ctk.CTkLabel(
            title_box,
            text="Autonomous Web Scraping & Structured Extraction Desktop",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.lbl_sub.pack(anchor="w")

        # Header Right Controls
        hdr_right = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_right.pack(side="right", padx=20, pady=14)

        # Status Capsule (Recessed/Sunken Pill)
        self.status_pill = ctk.CTkFrame(
            hdr_right,
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            corner_radius=12,
            height=34,
        )
        self.status_pill.pack(side="left", padx=(0, 10))

        self.status_dot = ctk.CTkLabel(
            self.status_pill,
            text="●",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            text_color=t["success"],
        )
        self.status_dot.pack(side="left", padx=(10, 4), pady=4)

        self.status_text = ctk.CTkLabel(
            self.status_pill,
            text="READY",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=10, weight="bold"),
            text_color=t["text"],
        )
        self.status_text.pack(side="left", padx=(0, 12), pady=4)

        # Theme Switcher Button (Light / Dark Mode)
        self.btn_theme = ctk.CTkButton(
            hdr_right,
            text="☀ Light",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=12,
            height=34,
            width=85,
            command=self.toggle_theme,
        )
        self.btn_theme.pack(side="left", padx=(0, 10))

        # Open Output Folder Button (Tactile Raised)
        self.btn_folder = ctk.CTkButton(
            hdr_right,
            text="Output Folder",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=12,
            height=34,
            command=self.open_output_folder,
        )
        self.btn_folder.pack(side="left")

        # 2. CONTROL CARD (Raised Neumorphic Surface for URL & Configuration)
        self.control_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=18,
        )
        self.control_card.pack(fill="x", padx=20, pady=(0, 12))

        # Row 1: URL Input Box & Scrape CTA Button
        url_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        url_row.pack(fill="x", padx=20, pady=(16, 12))

        self.lbl_url = ctk.CTkLabel(
            url_row,
            text="TARGET URL",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=11, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_url.pack(side="left", padx=(0, 14))

        # Sunken / Inset URL Input Field (Body Font for Clean Reading)
        self.url_entry = ctk.CTkEntry(
            url_row,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            text_color=t["text"],
            placeholder_text="Enter any URL (e.g. https://deprem.afad.gov.tr/last-earthquakes.html)...",
            placeholder_text_color=t["dim"],
            corner_radius=12,
            height=42,
        )
        self.url_entry.insert(0, "https://deprem.afad.gov.tr/last-earthquakes.html")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 14))
        self.url_entry.bind("<Return>", lambda e: self.start_scraping())

        # Glowing Tactile Action Button
        self.btn_scrape = ctk.CTkButton(
            url_row,
            text="SCRAPE DATA",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=12, weight="bold"),
            fg_color=t["accent_card"],
            hover_color=t["accent_hover"],
            border_color=t["accent"],
            border_width=1,
            text_color=t["accent_text"],
            corner_radius=12,
            height=42,
            width=150,
            command=self.start_scraping,
        )
        self.btn_scrape.pack(side="right")

        # Row 2: Engine Segmented Switch & Preset Options
        opts_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=20, pady=(0, 16))

        self.lbl_engine = ctk.CTkLabel(
            opts_row,
            text="Engine:",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            text_color=t["text_subtle"],
        )
        self.lbl_engine.pack(side="left", padx=(0, 8))

        # Modern Segmented Engine Button
        self.engine_segmented = ctk.CTkSegmentedButton(
            opts_row,
            values=["HTTP Client (Fast)", "Headless Browser (Playwright / Dynamic JS)"],
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["inset_bg"],
            selected_color=t["accent_card"],
            selected_hover_color=t["accent_hover"],
            unselected_color=t["inset_bg"],
            unselected_hover_color=t["btn_hover"],
            text_color=t["text"],
            corner_radius=10,
            height=32,
        )
        self.engine_segmented.set("HTTP Client (Fast)")
        self.engine_segmented.pack(side="left", padx=(0, 24))

        # Quick Presets Dropdown
        self.lbl_presets = ctk.CTkLabel(
            opts_row,
            text="Quick Presets:",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            text_color=t["text_subtle"],
        )
        self.lbl_presets.pack(side="left", padx=(0, 8))

        self.preset_menu = ctk.CTkOptionMenu(
            opts_row,
            values=[
                "AFAD Son Depremler",
                "Books to Scrape",
                "Quotes to Scrape",
                "Hacker News",
            ],
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            button_color=t["btn_hover"],
            button_hover_color=t["card_border"],
            dropdown_fg_color=t["card_bg"],
            dropdown_hover_color=t["btn_hover"],
            dropdown_text_color=t["text"],
            text_color=t["text"],
            corner_radius=10,
            height=32,
            width=180,
            command=self.on_preset_change,
        )
        self.preset_menu.set("AFAD Son Depremler")
        self.preset_menu.pack(side="left")

        # 3. MAIN DATA WORKSPACE (Large Raised Neumorphic Card)
        self.workspace_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=18,
        )
        self.workspace_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Workspace Header (Title & Instant Search Box)
        ws_hdr = ctk.CTkFrame(self.workspace_card, fg_color="transparent")
        ws_hdr.pack(fill="x", padx=20, pady=(16, 12))

        self.lbl_table_title = ctk.CTkLabel(
            ws_hdr,
            text="EXTRACTED DATASETS (0 RECORDS)",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=12, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_table_title.pack(side="left")

        # Inset Filter Entry (Body Font)
        search_box = ctk.CTkFrame(ws_hdr, fg_color="transparent")
        search_box.pack(side="right")

        self.filter_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="Filter records...",
            placeholder_text_color=t["dim"],
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=10,
            height=32,
            width=220,
        )
        self.filter_entry.pack(side="left")
        self.filter_entry.bind("<KeyRelease>", lambda e: self.filter_table())

        # Table Container with Inset Styling
        self.table_container = ctk.CTkFrame(
            self.workspace_card,
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            corner_radius=12,
        )
        self.table_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Modern Neumorphic Scrollbars
        self.y_scroll = ctk.CTkScrollbar(
            self.table_container,
            orientation="vertical",
            fg_color=t["inset_bg"],
            button_color=t["btn_border"],
            button_hover_color=t["accent"],
            corner_radius=6,
            width=12,
        )
        self.y_scroll.pack(side="right", fill="y", padx=(2, 4), pady=4)

        self.x_scroll = ctk.CTkScrollbar(
            self.table_container,
            orientation="horizontal",
            fg_color=t["inset_bg"],
            button_color=t["btn_border"],
            button_hover_color=t["accent"],
            corner_radius=6,
            height=12,
        )
        self.x_scroll.pack(side="bottom", fill="x", padx=4, pady=(2, 4))

        self.tree = ttk.Treeview(
            self.table_container,
            yscrollcommand=self.y_scroll.set,
            xscrollcommand=self.x_scroll.set,
            show="headings",
        )
        self.y_scroll.configure(command=self.tree.yview)
        self.x_scroll.configure(command=self.tree.xview)
        self.tree.pack(fill="both", expand=True, padx=(4, 0), pady=(4, 0))

        # 4. FOOTER STATUS BAR (Raised Neumorphic Capsule)
        self.footer_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=14,
            height=48,
        )
        self.footer_card.pack(fill="x", padx=20, pady=(0, 16))
        self.footer_card.pack_propagate(False)

        self.status_msg = ctk.CTkLabel(
            self.footer_card,
            text="Ready. Paste any web URL and click 'SCRAPE DATA'.",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.status_msg.pack(side="left", padx=20, pady=10)

        # Animated Progress Bar (hidden when idle)
        self.progress_bar = ctk.CTkProgressBar(
            self.footer_card,
            mode="indeterminate",
            width=160,
            height=8,
            corner_radius=4,
            fg_color=t["inset_bg"],
            progress_color=t["accent"],
        )

        # Action Buttons Right
        actions_box = ctk.CTkFrame(self.footer_card, fg_color="transparent")
        actions_box.pack(side="right", padx=16, pady=8)

        self.btn_csv = ctk.CTkButton(
            actions_box,
            text="Save CSV",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=10,
            height=30,
            width=90,
            command=self.save_csv,
        )
        self.btn_csv.pack(side="left", padx=(0, 8))

        self.btn_json = ctk.CTkButton(
            actions_box,
            text="Save JSON",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=10,
            height=30,
            width=90,
            command=self.save_json,
        )
        self.btn_json.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            actions_box,
            text="Clear",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["muted"],
            corner_radius=10,
            height=30,
            width=65,
            command=self.clear_table,
        )
        self.btn_clear.pack(side="left")

    def toggle_theme(self):
        """Toggle between Dark and Light mode dynamically."""
        new_mode = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme(new_mode)

    def apply_theme(self, mode: str):
        """Apply the selected theme to all widgets dynamically."""
        self.current_theme_name = mode
        self.theme = THEMES[mode]
        t = self.theme

        ctk.set_appearance_mode(mode)
        self.configure(fg_color=t["bg"])

        # Header Card
        self.header_card.configure(fg_color=t["card_bg"], border_color=t["card_border"])
        self.lbl_title.configure(text_color=t["accent"])
        self.lbl_sub.configure(text_color=t["text_subtle"])
        self.status_pill.configure(fg_color=t["inset_bg"], border_color=t["inset_border"])
        self.status_text.configure(text_color=t["text"])
        self.status_dot.configure(text_color=t["warning"] if self.is_scraping else t["success"])
        self.btn_theme.configure(
            text="☀ Light" if mode == "dark" else "🌙 Dark",
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            text_color=t["text"],
        )
        self.btn_folder.configure(
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            text_color=t["text"],
        )

        # Control Card
        self.control_card.configure(fg_color=t["card_bg"], border_color=t["card_border"])
        self.lbl_url.configure(text_color=t["accent"])
        self.url_entry.configure(
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            text_color=t["text"],
            placeholder_text_color=t["dim"],
        )
        self.btn_scrape.configure(
            fg_color=t["accent_card"],
            hover_color=t["accent_hover"],
            border_color=t["accent"],
            text_color=t["accent_text"],
        )
        self.lbl_engine.configure(text_color=t["text_subtle"])
        self.engine_segmented.configure(
            fg_color=t["inset_bg"],
            selected_color=t["accent_card"],
            selected_hover_color=t["accent_hover"],
            unselected_color=t["inset_bg"],
            unselected_hover_color=t["btn_hover"],
            text_color=t["text"],
        )
        self.lbl_presets.configure(text_color=t["text_subtle"])
        self.preset_menu.configure(
            fg_color=t["btn_raised"],
            button_color=t["btn_hover"],
            button_hover_color=t["card_border"],
            dropdown_fg_color=t["card_bg"],
            dropdown_hover_color=t["btn_hover"],
            dropdown_text_color=t["text"],
            text_color=t["text"],
        )

        # Main Workspace Card
        self.workspace_card.configure(fg_color=t["card_bg"], border_color=t["card_border"])
        self.lbl_table_title.configure(text_color=t["accent"])
        self.filter_entry.configure(
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            text_color=t["text"],
            placeholder_text_color=t["dim"],
        )
        self.table_container.configure(fg_color=t["inset_bg"], border_color=t["inset_border"])
        self.y_scroll.configure(
            fg_color=t["inset_bg"],
            button_color=t["btn_border"],
            button_hover_color=t["accent"],
        )
        self.x_scroll.configure(
            fg_color=t["inset_bg"],
            button_color=t["btn_border"],
            button_hover_color=t["accent"],
        )

        # Footer Card
        self.footer_card.configure(fg_color=t["card_bg"], border_color=t["card_border"])
        self.status_msg.configure(text_color=t["text_subtle"])
        self.progress_bar.configure(fg_color=t["inset_bg"], progress_color=t["accent"])
        self.btn_csv.configure(
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            text_color=t["text"],
        )
        self.btn_json.configure(
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            text_color=t["text"],
        )
        self.btn_clear.configure(
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            text_color=t["muted"],
        )

        # Treeview styling
        self._init_ttk_styles()

    # -------------------------------------------------------------------------
    # APP WORKFLOW & WORKERS
    # -------------------------------------------------------------------------
    def on_preset_change(self, choice: str):
        """Populate URL based on selected preset."""
        presets = {
            "AFAD Son Depremler": "https://deprem.afad.gov.tr/last-earthquakes.html",
            "Books to Scrape": "https://books.toscrape.com/",
            "Quotes to Scrape": "https://quotes.toscrape.com/",
            "Hacker News": "https://news.ycombinator.com/",
        }
        if choice in presets:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, presets[choice])

    def open_output_folder(self):
        """Open dedicated output folder in Windows Explorer silently without any terminal."""
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(DEFAULT_OUTPUT_DIR)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", DEFAULT_OUTPUT_DIR])

    def start_scraping(self):
        """Validate URL and initiate background extraction."""
        if self.is_scraping:
            return

        raw_url = self.url_entry.get().strip()
        if not raw_url:
            messagebox.showwarning("Missing URL", "Please enter a target web URL.")
            return

        if not is_valid_url(raw_url):
            messagebox.showerror("Invalid URL", f"The address '{raw_url}' is not a valid web URL.")
            return

        url = normalize_url(raw_url)
        use_browser = "Headless Browser" in self.engine_segmented.get()

        self.is_scraping = True
        self.btn_scrape.configure(state="disabled", text="EXTRACTING...")
        self.status_dot.configure(text_color=self.theme["warning"])
        self.status_text.configure(text="BUSY")
        self.status_msg.configure(text=f"Connecting to {url}...")

        self.progress_bar.pack(side="left", padx=16)
        self.progress_bar.start()

        threading.Thread(target=self._scrape_thread, args=(url, use_browser), daemon=True).start()

    def _scrape_thread(self, url: str, use_browser: bool):
        """Background extraction thread."""
        start_time = time.time()
        try:
            if use_browser:
                from core.browser_fetcher import fetch_page_browser
                self.after(0, lambda: self.status_msg.configure(text="Rendering dynamic page in Chromium engine..."))
                raw_html = fetch_page_browser(url)
            else:
                self.after(0, lambda: self.status_msg.configure(text="Fetching HTML response..."))
                resp = fetch_page(url)
                raw_html = resp.text

            self.after(0, lambda: self.status_msg.configure(text="Analyzing DOM patterns and data tables..."))
            soup = clean_html(raw_html)

            # Check bot protection walls
            block_reason = check_bot_protection(soup)
            if block_reason:
                msg = f"Anti-Bot Challenge Detected ({block_reason}). The target site served an access denial page."
                self.after(0, lambda: messagebox.showwarning("Anti-Bot Detected", msg))

            extractor = UniversalExtractor(base_url=url)
            records = extractor.extract_all(soup)

            elapsed = time.time() - start_time

            if not records:
                self.after(0, lambda: self._on_scrape_empty(url))
            else:
                default_file = derive_default_filename(url, ext="csv")
                dest_path = os.path.join(DEFAULT_OUTPUT_DIR, default_file)
                export_data(records, dest_path)
                self.last_saved_file = default_file
                self.after(0, lambda: self._on_scrape_success(records, default_file, elapsed))

        except Exception as err:
            self.after(0, lambda: self._on_scrape_error(err))
        finally:
            self.is_scraping = False
            self.after(0, self._reset_ui)

    def _on_scrape_success(self, records: list[dict], filename: str, elapsed: float):
        """Render records on UI thread."""
        self.current_records = records
        self.render_table(self.current_records)
        self.status_msg.configure(text=f"Successfully extracted {len(records)} records in {elapsed:.2f}s. Saved to output/{filename}")

    def _on_scrape_empty(self, url: str):
        """Handle no records."""
        self.status_msg.configure(text="No structured data records or tables found on page.")
        messagebox.showinfo("No Records", "No recurring item cards or data tables were detected on this page.")

    def _on_scrape_error(self, error: Exception):
        """Handle scrape error."""
        self.status_msg.configure(text=f"Extraction error: {error}")
        messagebox.showerror("Scraping Error", f"Extraction failed:\n{error}")

    def _reset_ui(self):
        """Restore buttons and indicators."""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_scrape.configure(state="normal", text="SCRAPE DATA")
        self.status_dot.configure(text_color=self.theme["success"])
        self.status_text.configure(text="READY")

    def render_table(self, records: list[dict]):
        """Populate treeview dynamically adapting to any dataset columns."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not records:
            self.lbl_table_title.configure(text="EXTRACTED DATASETS (0 RECORDS)")
            return

        all_keys = list(dict.fromkeys(k for row in records for k in row.keys()))

        # Remove redundant helper 'title' if a domain-specific column like 'Yer' or 'name' is present
        if "title" in all_keys and any(k in all_keys for k in ["Yer", "name", "headline", "item_name"]):
            all_keys.remove("title")

        cols = ["#"] + all_keys
        self.active_cols = cols

        # Configure dynamic column headers and proportions using Body Font
        self.tree.config(columns=cols)
        for col in cols:
            self.tree.heading(col, text=col)
            col_l = col.lower()
            if col == "#":
                self.tree.column(col, width=45, minwidth=35, anchor="center")
            elif "url" in col_l or "link" in col_l:
                self.tree.column(col, width=280, minwidth=180, anchor="w")
            elif any(d in col_l for d in ["tarih", "date", "time"]):
                self.tree.column(col, width=160, minwidth=120, anchor="center")
            elif any(y in col_l for y in ["yer", "title", "name", "description", "headline"]):
                self.tree.column(col, width=260, minwidth=180, anchor="w")
            elif any(m in col_l for m in ["büyüklük", "mag", "price", "rating", "derinlik", "enlem", "boylam", "tip"]):
                self.tree.column(col, width=95, minwidth=70, anchor="center")
            else:
                self.tree.column(col, width=120, minwidth=80, anchor="center")

        self._insert_rows(records)
        self.lbl_table_title.configure(text=f"EXTRACTED DATASETS ({len(records)} RECORDS)")

    def _insert_rows(self, records: list[dict]):
        """Insert records into treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.active_cols:
            return

        for i, row in enumerate(records, 1):
            values = [i]
            for col in self.active_cols[1:]:
                val = row.get(col, "")
                if col == "rating" and str(val).isdigit():
                    val = "*" * int(val)
                elif col == "price" and "currency" in row:
                    val = f"{row.get('currency', '')}{val}"
                values.append(val)
            self.tree.insert("", "end", values=values)

    def filter_table(self):
        """Filter table rows dynamically."""
        query = self.filter_entry.get().strip().lower()
        if not query:
            self._insert_rows(self.current_records)
            self.lbl_table_title.configure(text=f"EXTRACTED DATASETS ({len(self.current_records)} RECORDS)")
            return

        filtered = [
            r for r in self.current_records
            if any(query in str(v).lower() for v in r.values())
        ]
        self._insert_rows(filtered)
        self.lbl_table_title.configure(text=f"EXTRACTED DATASETS ({len(filtered)} OF {len(self.current_records)} RECORDS)")

    def save_csv(self):
        """Save extracted records directly into the output folder."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        filename = getattr(self, "last_saved_file", None)
        if not filename:
            raw_url = self.url_entry.get().strip() or "scraped_data"
            filename = derive_default_filename(raw_url, ext="csv")

        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        dest_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
        export_data(self.current_records, dest_path)
        self.status_msg.configure(text=f"Saved {len(self.current_records)} records to: output/{filename}")
        messagebox.showinfo("Saved", f"Records successfully saved to:\n\noutput/{filename}")

    def save_json(self):
        """Save extracted records directly as JSON into the output folder."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        raw_url = self.url_entry.get().strip() or "scraped_data"
        filename = derive_default_filename(raw_url, ext="json")

        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        dest_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
        export_data(self.current_records, dest_path)
        self.status_msg.configure(text=f"Saved {len(self.current_records)} records to: output/{filename}")
        messagebox.showinfo("Saved", f"Records successfully saved to:\n\noutput/{filename}")

    def clear_table(self):
        """Clear memory and reset table."""
        self.current_records = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_table_title.configure(text="EXTRACTED DATASETS (0 RECORDS)")
        self.status_msg.configure(text="Table cleared.")


def main():
    app = ScrapeAgentApp()
    app.mainloop()


if __name__ == "__main__":
    main()

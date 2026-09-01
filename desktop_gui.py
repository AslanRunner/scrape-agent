"""
ScrapeAgent - Modern Neumorphic Desktop Application.
Crafted with CustomTkinter featuring soft tactile cards, extruded controls,
sunken input fields, seamless dark scrollbars, Gotham geometric typography,
and zero-terminal execution.
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

# -----------------------------------------------------------------------------
# NEUMORPHIC DARK THEME PALETTE
# -----------------------------------------------------------------------------
NEU = {
    "bg": "#12151b",            # Deep graphite background
    "card_bg": "#1a1e27",       # Raised surface base
    "card_border": "#282f3d",   # Light top/left extrusion border
    "card_shadow": "#0b0d11",   # Deep bottom shadow
    "inset_bg": "#0f1217",      # Sunken input background
    "inset_border": "#222733",  # Inner recess stroke
    "btn_raised": "#222733",    # Tactile raised button
    "btn_hover": "#2d3444",     # Button hover state
    "btn_border": "#323a4b",    # Button highlight rim
    "accent": "#38bdf8",        # Luminous electric cyan
    "accent_hover": "#0ea5e9",  # Deep cyan hover
    "accent_text": "#041424",   # Contrast text on accent
    "accent_card": "#0284c7",   # Primary CTA button
    "text": "#f1f5f9",          # Primary crisp white
    "muted": "#94a3b8",         # Secondary cool gray
    "dim": "#64748b",           # Subdued tertiary
    "success": "#10b981",       # Emerald green dot
    "warning": "#f59e0b",       # Amber warning
    "error": "#ef4444",         # Rose red
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def detect_gotham_font() -> str:
    """Return Gotham if installed on system, otherwise Century Gothic (geometric equivalent)."""
    try:
        import tkinter.font as tkfont
        root = tk.Tk()
        root.withdraw()
        available = tkfont.families()
        root.destroy()
        for cand in ["Gotham", "Gotham Medium", "Gotham Bold", "Gotham-Book", "Century Gothic", "Segoe UI"]:
            if cand in available:
                return cand
    except Exception:
        pass
    return "Century Gothic"


FONT_FAMILY = detect_gotham_font()


class ScrapeAgentApp(ctk.CTk):
    """Neumorphic Desktop Application for ScrapeAgent."""

    def __init__(self):
        super().__init__()

        self.title("ScrapeAgent · Autonomous Data Extraction")
        self.geometry("1160x800")
        self.minsize(920, 620)
        self.configure(fg_color=NEU["bg"])

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
        """Configure native table to blend into Neumorphic card surface with zero harsh borders."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=NEU["card_bg"],
            foreground=NEU["text"],
            fieldbackground=NEU["card_bg"],
            rowheight=32,
            font=(FONT_FAMILY, 10),
            borderwidth=0,
            highlightthickness=0,
        )
        style.configure(
            "Treeview.Heading",
            background=NEU["btn_raised"],
            foreground=NEU["text"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            padding=8,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", NEU["card_border"])],
            foreground=[("selected", NEU["accent"])],
        )

    def _init_ui(self):
        # 1. TOP HEADER / MASTHEAD (Raised Neumorphic Card)
        self.header_card = ctk.CTkFrame(
            self,
            fg_color=NEU["card_bg"],
            border_color=NEU["card_border"],
            border_width=1,
            corner_radius=16,
            height=70,
        )
        self.header_card.pack(fill="x", padx=20, pady=(16, 12))
        self.header_card.pack_propagate(False)

        # Brand Title Left
        title_box = ctk.CTkFrame(self.header_card, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="⚡ ScrapeAgent",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=NEU["accent"],
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = ctk.CTkLabel(
            title_box,
            text="Autonomous Web Scraping & Structured Extraction Desktop",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=NEU["muted"],
        )
        self.lbl_sub.pack(anchor="w")

        # Header Right Controls
        hdr_right = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_right.pack(side="right", padx=20, pady=14)

        # Status Capsule (Recessed/Sunken Pill)
        self.status_pill = ctk.CTkFrame(
            hdr_right,
            fg_color=NEU["inset_bg"],
            border_color=NEU["inset_border"],
            border_width=1,
            corner_radius=12,
            height=34,
        )
        self.status_pill.pack(side="left", padx=(0, 12))

        self.status_dot = ctk.CTkLabel(
            self.status_pill,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=NEU["success"],
        )
        self.status_dot.pack(side="left", padx=(10, 4), pady=4)

        self.status_text = ctk.CTkLabel(
            self.status_pill,
            text="READY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=NEU["text"],
        )
        self.status_text.pack(side="left", padx=(0, 12), pady=4)

        # Open Output Folder Button (Tactile Raised)
        self.btn_folder = ctk.CTkButton(
            hdr_right,
            text="📁 Output Folder",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=NEU["btn_raised"],
            hover_color=NEU["btn_hover"],
            border_color=NEU["btn_border"],
            border_width=1,
            text_color=NEU["text"],
            corner_radius=12,
            height=34,
            command=self.open_output_folder,
        )
        self.btn_folder.pack(side="left")

        # 2. CONTROL CARD (Raised Neumorphic Surface for URL & Configuration)
        self.control_card = ctk.CTkFrame(
            self,
            fg_color=NEU["card_bg"],
            border_color=NEU["card_border"],
            border_width=1,
            corner_radius=18,
        )
        self.control_card.pack(fill="x", padx=20, pady=(0, 12))

        # Row 1: URL Input Box & Scrape CTA Button
        url_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        url_row.pack(fill="x", padx=20, pady=(16, 12))

        lbl_url = ctk.CTkLabel(
            url_row,
            text="TARGET URL",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=NEU["accent"],
        )
        lbl_url.pack(side="left", padx=(0, 14))

        # Sunken / Inset URL Input Field
        self.url_entry = ctk.CTkEntry(
            url_row,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color=NEU["inset_bg"],
            border_color=NEU["inset_border"],
            border_width=1,
            text_color=NEU["text"],
            placeholder_text="Enter any URL (e.g. https://deprem.afad.gov.tr/last-earthquakes.html)...",
            placeholder_text_color=NEU["dim"],
            corner_radius=12,
            height=42,
        )
        self.url_entry.insert(0, "https://deprem.afad.gov.tr/last-earthquakes.html")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 14))
        self.url_entry.bind("<Return>", lambda e: self.start_scraping())

        # Glowing Tactile Action Button
        self.btn_scrape = ctk.CTkButton(
            url_row,
            text="🚀 SCRAPE DATA",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=NEU["accent_card"],
            hover_color=NEU["accent_hover"],
            border_color=NEU["accent"],
            border_width=1,
            text_color="#ffffff",
            corner_radius=12,
            height=42,
            width=160,
            command=self.start_scraping,
        )
        self.btn_scrape.pack(side="right")

        # Row 2: Engine Segmented Switch & Preset Options
        opts_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=20, pady=(0, 16))

        lbl_engine = ctk.CTkLabel(
            opts_row,
            text="Engine:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=NEU["muted"],
        )
        lbl_engine.pack(side="left", padx=(0, 8))

        # Modern Segmented Engine Button
        self.engine_segmented = ctk.CTkSegmentedButton(
            opts_row,
            values=["HTTP Client (Fast)", "Headless Browser (Playwright / Dynamic JS)"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=NEU["inset_bg"],
            selected_color=NEU["accent_card"],
            selected_hover_color=NEU["accent_hover"],
            unselected_color=NEU["inset_bg"],
            unselected_hover_color=NEU["btn_hover"],
            corner_radius=10,
            height=32,
        )
        self.engine_segmented.set("HTTP Client (Fast)")
        self.engine_segmented.pack(side="left", padx=(0, 24))

        # Quick Presets Dropdown
        lbl_presets = ctk.CTkLabel(
            opts_row,
            text="Quick Presets:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=NEU["muted"],
        )
        lbl_presets.pack(side="left", padx=(0, 8))

        self.preset_menu = ctk.CTkOptionMenu(
            opts_row,
            values=[
                "AFAD Son Depremler",
                "Books to Scrape",
                "Quotes to Scrape",
                "Hacker News",
            ],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=NEU["btn_raised"],
            button_color=NEU["btn_hover"],
            button_hover_color=NEU["card_border"],
            dropdown_fg_color=NEU["card_bg"],
            dropdown_hover_color=NEU["btn_hover"],
            dropdown_text_color=NEU["text"],
            text_color=NEU["text"],
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
            fg_color=NEU["card_bg"],
            border_color=NEU["card_border"],
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=NEU["accent"],
        )
        self.lbl_table_title.pack(side="left")

        # Inset Filter Entry
        search_box = ctk.CTkFrame(ws_hdr, fg_color="transparent")
        search_box.pack(side="right")

        self.filter_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="🔍 Filter records...",
            placeholder_text_color=NEU["dim"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=NEU["inset_bg"],
            border_color=NEU["inset_border"],
            border_width=1,
            text_color=NEU["text"],
            corner_radius=10,
            height=32,
            width=220,
        )
        self.filter_entry.pack(side="left")
        self.filter_entry.bind("<KeyRelease>", lambda e: self.filter_table())

        # Table Container with Dark Inset Styling (No white lines or bars)
        table_container = ctk.CTkFrame(
            self.workspace_card,
            fg_color=NEU["inset_bg"],
            border_color=NEU["inset_border"],
            border_width=1,
            corner_radius=12,
        )
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Modern Dark Neumorphic Scrollbars (Zero white borders/troughs)
        self.y_scroll = ctk.CTkScrollbar(
            table_container,
            orientation="vertical",
            fg_color=NEU["inset_bg"],
            button_color=NEU["btn_border"],
            button_hover_color=NEU["accent"],
            corner_radius=6,
            width=12,
        )
        self.y_scroll.pack(side="right", fill="y", padx=(2, 4), pady=4)

        self.x_scroll = ctk.CTkScrollbar(
            table_container,
            orientation="horizontal",
            fg_color=NEU["inset_bg"],
            button_color=NEU["btn_border"],
            button_hover_color=NEU["accent"],
            corner_radius=6,
            height=12,
        )
        self.x_scroll.pack(side="bottom", fill="x", padx=4, pady=(2, 4))

        self.tree = ttk.Treeview(
            table_container,
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
            fg_color=NEU["card_bg"],
            border_color=NEU["card_border"],
            border_width=1,
            corner_radius=14,
            height=48,
        )
        self.footer_card.pack(fill="x", padx=20, pady=(0, 16))
        self.footer_card.pack_propagate(False)

        self.status_msg = ctk.CTkLabel(
            self.footer_card,
            text="Ready. Paste any web URL and click 'Scrape Data'.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=NEU["muted"],
        )
        self.status_msg.pack(side="left", padx=20, pady=10)

        # Animated Progress Bar (hidden when idle)
        self.progress_bar = ctk.CTkProgressBar(
            self.footer_card,
            mode="indeterminate",
            width=160,
            height=8,
            corner_radius=4,
            fg_color=NEU["inset_bg"],
            progress_color=NEU["accent"],
        )

        # Action Buttons Right
        actions_box = ctk.CTkFrame(self.footer_card, fg_color="transparent")
        actions_box.pack(side="right", padx=16, pady=8)

        self.btn_csv = ctk.CTkButton(
            actions_box,
            text="💾 Save CSV",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=NEU["btn_raised"],
            hover_color=NEU["btn_hover"],
            border_color=NEU["btn_border"],
            border_width=1,
            text_color=NEU["text"],
            corner_radius=10,
            height=30,
            width=100,
            command=self.save_csv,
        )
        self.btn_csv.pack(side="left", padx=(0, 8))

        self.btn_json = ctk.CTkButton(
            actions_box,
            text="💾 Save JSON",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=NEU["btn_raised"],
            hover_color=NEU["btn_hover"],
            border_color=NEU["btn_border"],
            border_width=1,
            text_color=NEU["text"],
            corner_radius=10,
            height=30,
            width=100,
            command=self.save_json,
        )
        self.btn_json.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            actions_box,
            text="✕ Clear",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=NEU["btn_raised"],
            hover_color=NEU["btn_hover"],
            border_color=NEU["btn_border"],
            border_width=1,
            text_color=NEU["dim"],
            corner_radius=10,
            height=30,
            width=70,
            command=self.clear_table,
        )
        self.btn_clear.pack(side="left")

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
        """Open project directory in Windows Explorer."""
        path = os.path.abspath(PROJECT_ROOT)
        if sys.platform == "win32":
            os.system(f'explorer "{path}"')
        else:
            messagebox.showinfo("Folder Location", path)

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
        self.btn_scrape.configure(state="disabled", text="⏳ EXTRACTING...")
        self.status_dot.configure(text_color=NEU["warning"])
        self.status_text.configure(text="EXTRACTING")
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
                export_data(records, default_file)
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
        self.status_msg.configure(text=f"✓ Successfully extracted {len(records)} records in {elapsed:.2f}s. Saved to '{filename}'.")

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
        self.btn_scrape.configure(state="normal", text="🚀 SCRAPE DATA")
        self.status_dot.configure(text_color=NEU["success"])
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

        # Configure dynamic column headers and proportions
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
        """Save extracted records as CSV."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Save Extracted Data to CSV",
        )
        if path:
            export_data(self.current_records, path)
            messagebox.showinfo("Export Complete", f"Successfully exported {len(self.current_records)} records to:\n{path}")

    def save_json(self):
        """Save extracted records as JSON."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Extracted Data to JSON",
        )
        if path:
            export_data(self.current_records, path)
            messagebox.showinfo("Export Complete", f"Successfully exported {len(self.current_records)} records to:\n{path}")

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

"""ScrapeAgent desktop GUI."""
import os
import sys
import threading
import time
from urllib.parse import urlparse
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent import is_valid_url, normalize_url, derive_default_filename, check_bot_protection
from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.extractor import UniversalExtractor
from core.exporter import export_data
from config import DEFAULT_OUTPUT_DIR

THEMES = {
    "dark": {
        "bg": "#0a0b0e",
        "card_bg": "#12151c",
        "card_border": "#1e2433",
        "inset_bg": "#0d0f14",
        "inset_border": "#1c2230",
        "btn_raised": "#181e2b",
        "btn_hover": "#222b3d",
        "btn_border": "#2a354b",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "accent_text": "#ffffff",
        "accent_card": "#2563eb",
        "text": "#f8fafc",
        "text_subtle": "#94a3b8",
        "muted": "#64748b",
        "dim": "#475569",
        "success": "#10b981",
        "warning": "#3b82f6",
        "error": "#ef4444",
        "tree_bg": "#12151c",
        "tree_fg": "#f8fafc",
        "tree_head_bg": "#181e2b",
        "tree_head_fg": "#f8fafc",
        "tree_selected": "#1e293b",
    },
    "light": {
        "bg": "#f8fafc",
        "card_bg": "#ffffff",
        "card_border": "#e2e8f0",
        "inset_bg": "#f1f5f9",
        "inset_border": "#cbd5e1",
        "btn_raised": "#f1f5f9",
        "btn_hover": "#e2e8f0",
        "btn_border": "#cbd5e1",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_text": "#ffffff",
        "accent_card": "#2563eb",
        "text": "#0f172a",
        "text_subtle": "#334155",
        "muted": "#64748b",
        "dim": "#94a3b8",
        "success": "#059669",
        "warning": "#2563eb",
        "error": "#dc2626",
        "tree_bg": "#ffffff",
        "tree_fg": "#0f172a",
        "tree_head_bg": "#f1f5f9",
        "tree_head_fg": "#0f172a",
        "tree_selected": "#dbeafe",
    },
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_DISPLAY = "Century Gothic"
FONT_BODY = "Segoe UI"


class ScrapeAgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_theme_name = "dark"
        self.theme = THEMES["dark"]

        self.title("ScrapeAgent")
        self.geometry("1160x800")
        self.minsize(920, 620)
        self.configure(fg_color=self.theme["bg"])

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

        # Header
        self.header_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=14,
            height=66,
        )
        self.header_card.pack(fill="x", padx=20, pady=(16, 12))
        self.header_card.pack_propagate(False)

        title_box = ctk.CTkFrame(self.header_card, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="ScrapeAgent",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=20, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = ctk.CTkLabel(
            title_box,
            text="Web Scraping & Data Extraction Tool",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.lbl_sub.pack(anchor="w")

        hdr_right = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_right.pack(side="right", padx=20, pady=14)

        self.status_pill = ctk.CTkFrame(
            hdr_right,
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            corner_radius=10,
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
            text="Ready",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=10, weight="bold"),
            text_color=t["text"],
        )
        self.status_text.pack(side="left", padx=(0, 12), pady=4)

        self.btn_theme = ctk.CTkButton(
            hdr_right,
            text="☀ Light Mode",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=10,
            height=34,
            width=96,
            command=self.toggle_theme,
        )
        self.btn_theme.pack(side="left", padx=(0, 10))

        self.btn_folder = ctk.CTkButton(
            hdr_right,
            text="Output Folder",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=10,
            height=34,
            command=self.open_output_folder,
        )
        self.btn_folder.pack(side="left")

        # Controls
        self.control_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=14,
        )
        self.control_card.pack(fill="x", padx=20, pady=(0, 12))

        url_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        url_row.pack(fill="x", padx=20, pady=(16, 12))

        self.lbl_url = ctk.CTkLabel(
            url_row,
            text="URL",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=11, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_url.pack(side="left", padx=(0, 14))

        self.url_entry = ctk.CTkEntry(
            url_row,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            text_color=t["text"],
            placeholder_text="https://...",
            placeholder_text_color=t["dim"],
            corner_radius=10,
            height=40,
        )
        self.url_entry.insert(0, "https://quotes.toscrape.com/")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 14))
        self.url_entry.bind("<Return>", lambda e: self.start_scraping())

        self.btn_scrape = ctk.CTkButton(
            url_row,
            text="Scrape Data",
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            fg_color=t["accent_card"],
            hover_color=t["accent_hover"],
            border_color=t["accent"],
            border_width=1,
            text_color=t["accent_text"],
            corner_radius=10,
            height=40,
            width=130,
            command=self.start_scraping,
        )
        self.btn_scrape.pack(side="right")

        opts_row = ctk.CTkFrame(self.control_card, fg_color="transparent")
        opts_row.pack(fill="x", padx=20, pady=(0, 16))

        self.lbl_engine = ctk.CTkLabel(
            opts_row,
            text="Engine:",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.lbl_engine.pack(side="left", padx=(0, 8))

        self.engine_segmented = ctk.CTkSegmentedButton(
            opts_row,
            values=["HTTP (Fast)", "Browser (Playwright)"],
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["inset_bg"],
            selected_color=t["accent_card"],
            selected_hover_color=t["accent_hover"],
            unselected_color=t["inset_bg"],
            unselected_hover_color=t["btn_hover"],
            text_color=t["text"],
            corner_radius=8,
            height=30,
        )
        self.engine_segmented.set("HTTP (Fast)")
        self.engine_segmented.pack(side="left", padx=(0, 24))

        self.lbl_presets = ctk.CTkLabel(
            opts_row,
            text="Presets:",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.lbl_presets.pack(side="left", padx=(0, 8))

        self.preset_menu = ctk.CTkOptionMenu(
            opts_row,
            values=[
                "Quotes to Scrape",
                "Books to Scrape",
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
            corner_radius=8,
            height=30,
            width=160,
            command=self.on_preset_change,
        )
        self.preset_menu.set("Quotes to Scrape")
        self.preset_menu.pack(side="left")

        # Table area
        self.workspace_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=14,
        )
        self.workspace_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        ws_hdr = ctk.CTkFrame(self.workspace_card, fg_color="transparent")
        ws_hdr.pack(fill="x", padx=20, pady=(14, 10))

        self.lbl_table_title = ctk.CTkLabel(
            ws_hdr,
            text="Extracted Data (0 records)",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=12, weight="bold"),
            text_color=t["accent"],
        )
        self.lbl_table_title.pack(side="left")

        search_box = ctk.CTkFrame(ws_hdr, fg_color="transparent")
        search_box.pack(side="right")

        self.filter_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="Search in table...",
            placeholder_text_color=t["dim"],
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=8,
            height=30,
            width=200,
        )
        self.filter_entry.pack(side="left")
        self.filter_entry.bind("<KeyRelease>", lambda e: self.filter_table())

        self.table_container = ctk.CTkFrame(
            self.workspace_card,
            fg_color=t["inset_bg"],
            border_color=t["inset_border"],
            border_width=1,
            corner_radius=10,
        )
        self.table_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

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

        # Footer
        self.footer_card = ctk.CTkFrame(
            self,
            fg_color=t["card_bg"],
            border_color=t["card_border"],
            border_width=1,
            corner_radius=12,
            height=46,
        )
        self.footer_card.pack(fill="x", padx=20, pady=(0, 16))
        self.footer_card.pack_propagate(False)

        self.status_msg = ctk.CTkLabel(
            self.footer_card,
            text="Ready. Enter a URL and click 'Scrape Data'.",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=t["text_subtle"],
        )
        self.status_msg.pack(side="left", padx=20, pady=8)

        self.progress_bar = ctk.CTkProgressBar(
            self.footer_card,
            mode="indeterminate",
            width=140,
            height=6,
            corner_radius=3,
            fg_color=t["inset_bg"],
            progress_color=t["accent"],
        )

        actions_box = ctk.CTkFrame(self.footer_card, fg_color="transparent")
        actions_box.pack(side="right", padx=14, pady=6)

        self.btn_csv = ctk.CTkButton(
            actions_box,
            text="Export CSV",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=8,
            height=28,
            width=84,
            command=self.save_csv,
        )
        self.btn_csv.pack(side="left", padx=(0, 6))

        self.btn_json = ctk.CTkButton(
            actions_box,
            text="Export JSON",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["text"],
            corner_radius=8,
            height=28,
            width=84,
            command=self.save_json,
        )
        self.btn_json.pack(side="left", padx=(0, 6))

        self.btn_clear = ctk.CTkButton(
            actions_box,
            text="Clear",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=t["btn_raised"],
            hover_color=t["btn_hover"],
            border_color=t["btn_border"],
            border_width=1,
            text_color=t["muted"],
            corner_radius=8,
            height=28,
            width=60,
            command=self.clear_table,
        )
        self.btn_clear.pack(side="left")

    def toggle_theme(self):
        new_mode = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme(new_mode)

    def apply_theme(self, mode: str):
        self.current_theme_name = mode
        self.theme = THEMES[mode]
        t = self.theme

        ctk.set_appearance_mode(mode)
        self.configure(fg_color=t["bg"])

        self.header_card.configure(fg_color=t["card_bg"], border_color=t["card_border"])
        self.lbl_title.configure(text_color=t["accent"])
        self.lbl_sub.configure(text_color=t["text_subtle"])
        self.status_pill.configure(fg_color=t["inset_bg"], border_color=t["inset_border"])
        self.status_text.configure(text_color=t["text"])
        self.status_dot.configure(text_color=t["warning"] if self.is_scraping else t["success"])
        self.btn_theme.configure(
            text="☀ Light Mode" if mode == "dark" else "🌙 Dark Mode",
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

        self._init_ttk_styles()

    def on_preset_change(self, choice: str):
        presets = {
            "Quotes to Scrape": "https://quotes.toscrape.com/",
            "Books to Scrape": "https://books.toscrape.com/",
            "Hacker News": "https://news.ycombinator.com/",
        }
        if choice in presets:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, presets[choice])

    def open_output_folder(self):
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(DEFAULT_OUTPUT_DIR)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", DEFAULT_OUTPUT_DIR])

    def start_scraping(self):
        if self.is_scraping:
            return

        raw_url = self.url_entry.get().strip()
        if not raw_url:
            messagebox.showwarning("Missing URL", "Please enter a target web URL.")
            return

        if not is_valid_url(raw_url):
            messagebox.showerror("Invalid URL", f"The entered address is not a valid web URL:\n'{raw_url}'")
            return

        url = normalize_url(raw_url)
        use_browser = "Playwright" in self.engine_segmented.get()

        self.is_scraping = True
        self.btn_scrape.configure(state="disabled", text="Scraping...")
        self.status_dot.configure(text_color=self.theme["warning"])
        self.status_text.configure(text="Working")
        self.status_msg.configure(text=f"Connecting to {url}...")

        self.progress_bar.pack(side="left", padx=16)
        self.progress_bar.start()

        threading.Thread(target=self._scrape_thread, args=(url, use_browser), daemon=True).start()

    def _scrape_thread(self, url: str, use_browser: bool):
        start_time = time.time()
        try:
            if use_browser:
                from core.browser_fetcher import fetch_page_browser
                self.after(0, lambda: self.status_msg.configure(text="Rendering page in browser..."))
                raw_html = fetch_page_browser(url)
            else:
                self.after(0, lambda: self.status_msg.configure(text="Fetching HTML response..."))
                resp = fetch_page(url)
                raw_html = resp.text

            self.after(0, lambda: self.status_msg.configure(text="Parsing page content..."))
            soup = clean_html(raw_html)

            block_reason = check_bot_protection(soup)
            if block_reason:
                msg = f"Bot protection detected ({block_reason}). Access was denied."
                self.after(0, lambda: messagebox.showwarning("Bot Protection", msg))

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
        self.current_records = records
        self.render_table(self.current_records)
        self.status_msg.configure(text=f"Extracted {len(records)} records ({elapsed:.2f}s). Saved to output/{filename}")

    def _on_scrape_empty(self, url: str):
        self.status_msg.configure(text="No structured data or tables found on page.")
        messagebox.showinfo("No Data Found", "No recurring item cards or data tables were detected on this page.")

    def _on_scrape_error(self, error: Exception):
        self.status_msg.configure(text=f"Error: {error}")
        messagebox.showerror("Scraping Error", f"Extraction failed:\n{error}")

    def _reset_ui(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_scrape.configure(state="normal", text="Scrape Data")
        self.status_dot.configure(text_color=self.theme["success"])
        self.status_text.configure(text="Ready")

    def render_table(self, records: list[dict]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not records:
            self.lbl_table_title.configure(text="Extracted Data (0 records)")
            return

        all_keys = list(dict.fromkeys(k for row in records for k in row.keys()))

        if "title" in all_keys and any(k in all_keys for k in ["name", "headline", "item_name"]):
            all_keys.remove("title")

        cols = ["#"] + all_keys
        self.active_cols = cols

        self.tree.config(columns=cols)
        for col in cols:
            self.tree.heading(col, text=col)
            col_l = col.lower()
            if col == "#":
                self.tree.column(col, width=45, minwidth=35, anchor="center")
            elif "url" in col_l or "link" in col_l:
                self.tree.column(col, width=280, minwidth=180, anchor="w")
            elif any(d in col_l for d in ["date", "time"]):
                self.tree.column(col, width=160, minwidth=120, anchor="center")
            elif any(y in col_l for y in ["title", "name", "description", "headline", "location"]):
                self.tree.column(col, width=260, minwidth=180, anchor="w")
            elif any(m in col_l for m in ["price", "rating", "mag", "depth", "type", "count"]):
                self.tree.column(col, width=95, minwidth=70, anchor="center")
            else:
                self.tree.column(col, width=120, minwidth=80, anchor="center")

        self._insert_rows(records)
        self.lbl_table_title.configure(text=f"Extracted Data ({len(records)} records)")

    def _insert_rows(self, records: list[dict]):
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
        query = self.filter_entry.get().strip().lower()
        if not query:
            self._insert_rows(self.current_records)
            self.lbl_table_title.configure(text=f"Extracted Data ({len(self.current_records)} records)")
            return

        filtered = [
            r for r in self.current_records
            if any(query in str(v).lower() for v in r.values())
        ]
        self._insert_rows(filtered)
        self.lbl_table_title.configure(text=f"Extracted Data ({len(filtered)} / {len(self.current_records)} records)")

    def save_csv(self):
        if not self.current_records:
            messagebox.showwarning("Warning", "No records available to export.")
            return

        filename = getattr(self, "last_saved_file", None)
        if not filename:
            raw_url = self.url_entry.get().strip() or "data"
            filename = derive_default_filename(raw_url, ext="csv")

        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        dest_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
        export_data(self.current_records, dest_path)
        self.status_msg.configure(text=f"Saved {len(self.current_records)} records to: output/{filename}")
        messagebox.showinfo("Success", f"Records saved to:\n\noutput/{filename}")

    def save_json(self):
        if not self.current_records:
            messagebox.showwarning("Warning", "No records available to export.")
            return

        raw_url = self.url_entry.get().strip() or "data"
        filename = derive_default_filename(raw_url, ext="json")

        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        dest_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
        export_data(self.current_records, dest_path)
        self.status_msg.configure(text=f"Saved {len(self.current_records)} records to: output/{filename}")
        messagebox.showinfo("Success", f"Records saved to:\n\noutput/{filename}")

    def clear_table(self):
        self.current_records = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_table_title.configure(text="Extracted Data (0 records)")
        self.status_msg.configure(text="Table cleared.")


def main():
    app = ScrapeAgentApp()
    app.mainloop()


if __name__ == "__main__":
    main()

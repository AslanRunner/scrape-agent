"""
ScrapeAgent - Native Windows Desktop Application.
A zero-terminal, instant-launch graphical user interface for universal web scraping,
data extraction, interactive table exploration, and CSV/JSON exporting.
"""
import os
import sys
import threading
import time
from urllib.parse import urlparse

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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
# THEME: EXECUTIVE OBSIDIAN & ELECTRIC CYAN
# -----------------------------------------------------------------------------
THEME = {
    "bg": "#090d16",
    "surface": "#111827",
    "card": "#182234",
    "subtle": "#1f293d",
    "border": "#28354d",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "accent": "#38bdf8",
    "accent_hover": "#0ea5e9",
    "accent_text": "#041424",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "input_bg": "#0f172a",
}


class ScrapeAgentApp:
    """Zero-terminal native desktop application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ScrapeAgent · Autonomous Data Extraction")
        self.root.geometry("1120x760")
        self.root.minsize(860, 580)
        self.root.configure(bg=THEME["bg"])

        self.current_records = []
        self.is_scraping = False

        self._init_styles()
        self._init_ui()

    def _init_styles(self):
        """Configure clean ttk styling."""
        style = ttk.Style()
        style.theme_use("clam")

        # Table Styling
        style.configure(
            "Treeview",
            background=THEME["surface"],
            foreground=THEME["text"],
            fieldbackground=THEME["surface"],
            rowheight=30,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["card"],
            foreground=THEME["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=8,
        )
        style.map(
            "Treeview",
            background=[("selected", THEME["border"])],
            foreground=[("selected", THEME["accent"])],
        )

        # Scrollbars
        style.configure("Vertical.TScrollbar", background=THEME["card"], troughcolor=THEME["surface"], borderwidth=0)
        style.configure("Horizontal.TScrollbar", background=THEME["card"], troughcolor=THEME["surface"], borderwidth=0)

        # Progressbar
        style.configure("Horizontal.TProgressbar", background=THEME["accent"], troughcolor=THEME["surface"], borderwidth=0)

    def _init_ui(self):
        t = THEME

        # 1. TOP MASTHEAD
        self.header = tk.Frame(self.root, bg=t["surface"], padx=20, pady=12, highlightthickness=1, highlightbackground=t["border"])
        self.header.pack(fill="x", side="top")

        title_box = tk.Frame(self.header, bg=t["surface"])
        title_box.pack(side="left")

        tk.Label(title_box, text="ScrapeAgent", font=("Segoe UI", 18, "bold"), fg=t["accent"], bg=t["surface"]).pack(anchor="w")
        tk.Label(
            title_box,
            text="Autonomous Web Scraping & Structured Data Extraction",
            font=("Segoe UI", 9),
            fg=t["muted"],
            bg=t["surface"],
        ).pack(anchor="w")

        # Header Right
        hdr_right = tk.Frame(self.header, bg=t["surface"])
        hdr_right.pack(side="right")

        self.status_badge = tk.Label(
            hdr_right,
            text="● READY",
            font=("Segoe UI", 9, "bold"),
            fg=t["success"],
            bg=t["subtle"],
            padx=12,
            pady=4,
        )
        self.status_badge.pack(side="left", padx=(0, 10))

        self.btn_folder = tk.Button(
            hdr_right,
            text="📁 Output Folder",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["text"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.open_output_folder,
        )
        self.btn_folder.pack(side="left")

        # 2. CONTROL CARD (URL INPUT & ENGINE SELECTOR)
        self.control_card = tk.Frame(self.root, bg=t["surface"], padx=18, pady=14, highlightthickness=1, highlightbackground=t["border"])
        self.control_card.pack(fill="x", padx=20, pady=(14, 10))

        # Row 1: URL input bar
        url_row = tk.Frame(self.control_card, bg=t["surface"])
        url_row.pack(fill="x", pady=(0, 10))

        tk.Label(url_row, text="TARGET URL:", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["surface"]).pack(side="left", padx=(0, 10))

        self.url_entry = tk.Entry(
            url_row,
            font=("Segoe UI", 10),
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["accent"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=t["border"],
        )
        self.url_entry.insert(0, "https://books.toscrape.com/")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 12), ipady=5)
        self.url_entry.bind("<Return>", lambda e: self.start_scraping())

        self.btn_scrape = tk.Button(
            url_row,
            text="🚀 SCRAPE DATA",
            font=("Segoe UI", 10, "bold"),
            bg=t["accent"],
            fg=t["accent_text"],
            activebackground=t["accent_hover"],
            activeforeground=t["accent_text"],
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2",
            command=self.start_scraping,
        )
        self.btn_scrape.pack(side="right")

        # Row 2: Engine Selector & Presets
        options_row = tk.Frame(self.control_card, bg=t["surface"])
        options_row.pack(fill="x")

        self.engine_var = tk.StringVar(value="http")
        tk.Label(options_row, text="Engine:", font=("Segoe UI", 9, "bold"), fg=t["muted"], bg=t["surface"]).pack(side="left", padx=(0, 6))

        r_http = tk.Radiobutton(
            options_row,
            text="HTTP Client (Fast)",
            variable=self.engine_var,
            value="http",
            bg=t["surface"],
            fg=t["text"],
            selectcolor=t["card"],
            activebackground=t["surface"],
            activeforeground=t["accent"],
            font=("Segoe UI", 9),
        )
        r_http.pack(side="left", padx=(0, 12))

        r_browser = tk.Radiobutton(
            options_row,
            text="Headless Browser (Playwright / Dynamic JS)",
            variable=self.engine_var,
            value="browser",
            bg=t["surface"],
            fg=t["text"],
            selectcolor=t["card"],
            activebackground=t["surface"],
            activeforeground=t["accent"],
            font=("Segoe UI", 9),
        )
        r_browser.pack(side="left", padx=(0, 20))

        # Quick Presets
        tk.Label(options_row, text="Presets:", font=("Segoe UI", 9, "bold"), fg=t["muted"], bg=t["surface"]).pack(side="left", padx=(0, 6))
        self.preset_var = tk.StringVar(value="Select Preset...")
        presets = ["Books to Scrape", "Quotes to Scrape", "Hacker News"]
        preset_dropdown = ttk.Combobox(options_row, values=presets, textvariable=self.preset_var, state="readonly", width=18)
        preset_dropdown.pack(side="left")
        preset_dropdown.bind("<<ComboboxSelected>>", self.on_preset_change)

        # 3. FULL-HEIGHT DATA TABLE WORKSPACE
        self.table_container = tk.Frame(self.root, bg=t["surface"], padx=18, pady=12, highlightthickness=1, highlightbackground=t["border"])
        self.table_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Table Header Bar (Title & Search/Filter)
        tbl_header = tk.Frame(self.table_container, bg=t["surface"])
        tbl_header.pack(fill="x", pady=(0, 10))

        self.table_title = tk.Label(
            tbl_header,
            text="EXTRACTED DATASETS (0)",
            font=("Segoe UI", 10, "bold"),
            fg=t["accent"],
            bg=t["surface"],
        )
        self.table_title.pack(side="left")

        # Instant search filter box
        search_box = tk.Frame(tbl_header, bg=t["surface"])
        search_box.pack(side="right")

        tk.Label(search_box, text="Filter Table:", font=("Segoe UI", 9), fg=t["muted"], bg=t["surface"]).pack(side="left", padx=(0, 6))
        self.filter_entry = tk.Entry(
            search_box,
            font=("Segoe UI", 9),
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["accent"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=t["border"],
            width=22,
        )
        self.filter_entry.pack(side="left")
        self.filter_entry.bind("<KeyRelease>", lambda e: self.filter_table())

        # Treeview with full scrollbars
        tree_frame = tk.Frame(self.table_container, bg=t["surface"])
        tree_frame.pack(fill="both", expand=True)

        self.y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", style="Vertical.TScrollbar")
        self.y_scroll.pack(side="right", fill="y")

        self.x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", style="Horizontal.TScrollbar")
        self.x_scroll.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=self.y_scroll.set,
            xscrollcommand=self.x_scroll.set,
            columns=("idx", "title", "price", "rating", "availability", "url"),
            show="headings",
        )
        self.y_scroll.config(command=self.tree.yview)
        self.x_scroll.config(command=self.tree.xview)

        self.tree.heading("idx", text="#")
        self.tree.heading("title", text="Title / Item Name")
        self.tree.heading("price", text="Price")
        self.tree.heading("rating", text="Rating")
        self.tree.heading("availability", text="Availability")
        self.tree.heading("url", text="Detail URL")

        self.tree.column("idx", width=50, anchor="center")
        self.tree.column("title", width=420, anchor="w")
        self.tree.column("price", width=95, anchor="center")
        self.tree.column("rating", width=90, anchor="center")
        self.tree.column("availability", width=120, anchor="center")
        self.tree.column("url", width=340, anchor="w")

        self.tree.pack(fill="both", expand=True)

        # 4. BOTTOM ACTION & STATUS BAR
        self.footer = tk.Frame(self.root, bg=t["surface"], padx=20, pady=8, highlightthickness=1, highlightbackground=t["border"])
        self.footer.pack(fill="x", side="bottom")

        # Left status text
        self.status_label = tk.Label(self.footer, text="Ready. Paste a URL and click 'Scrape Data'.", font=("Segoe UI", 9), fg=t["muted"], bg=t["surface"])
        self.status_label.pack(side="left")

        # Center Progress Bar (hidden by default)
        self.progress_bar = ttk.Progressbar(self.footer, orient="horizontal", mode="indeterminate", length=180, style="Horizontal.TProgressbar")

        # Right Action Buttons
        actions_frame = tk.Frame(self.footer, bg=t["surface"])
        actions_frame.pack(side="right")

        self.btn_csv = tk.Button(
            actions_frame,
            text="💾 Save CSV",
            font=("Segoe UI", 9, "bold"),
            bg=t["card"],
            fg=t["text"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.save_csv,
        )
        self.btn_csv.pack(side="left", padx=(0, 8))

        self.btn_json = tk.Button(
            actions_frame,
            text="💾 Save JSON",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["text"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.save_json,
        )
        self.btn_json.pack(side="left", padx=(0, 8))

        self.btn_clear = tk.Button(
            actions_frame,
            text="✕ Clear",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["muted"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.clear_table,
        )
        self.btn_clear.pack(side="left")

    # -------------------------------------------------------------------------
    # APP ACTIONS & WORKERS
    # -------------------------------------------------------------------------
    def on_preset_change(self, event=None):
        """Populate URL based on selected preset."""
        choice = self.preset_var.get()
        presets = {
            "Books to Scrape": "https://books.toscrape.com/",
            "Quotes to Scrape": "https://quotes.toscrape.com/",
            "Hacker News": "https://news.ycombinator.com/",
        }
        if choice in presets:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, presets[choice])

    def open_output_folder(self):
        """Open project directory in Windows Explorer."""
        path = os.path.abspath(PROJECT_ROOT)
        if sys.platform == "win32":
            os.system(f'explorer "{path}"')
        else:
            messagebox.showinfo("Folder Location", path)

    def start_scraping(self):
        """Validate input and launch background extraction thread."""
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
        use_browser = self.engine_var.get() == "browser"

        self.is_scraping = True
        self.btn_scrape.config(state="disabled", text="⏳ EXTRACTING...")
        self.status_badge.config(text="● EXTRACTING", fg=THEME["warning"])
        self.status_label.config(text=f"Connecting to {url}...")

        self.progress_bar.pack(side="left", padx=20)
        self.progress_bar.start(10)

        threading.Thread(target=self._scrape_thread, args=(url, use_browser), daemon=True).start()

    def _scrape_thread(self, url: str, use_browser: bool):
        """Background extraction thread."""
        start_time = time.time()
        try:
            if use_browser:
                from core.browser_fetcher import fetch_page_browser
                self.root.after(0, lambda: self.status_label.config(text="Rendering page in Chromium browser..."))
                raw_html = fetch_page_browser(url)
            else:
                self.root.after(0, lambda: self.status_label.config(text="Fetching HTML response..."))
                resp = fetch_page(url)
                raw_html = resp.text

            self.root.after(0, lambda: self.status_label.config(text="Analyzing DOM patterns..."))
            soup = clean_html(raw_html)

            # Check bot blocks
            block_reason = check_bot_protection(soup)
            if block_reason:
                msg = f"Anti-Bot Challenge Detected ({block_reason}). The site served a verification screen."
                self.root.after(0, lambda: messagebox.showwarning("Anti-Bot Detected", msg))

            extractor = UniversalExtractor(base_url=url)
            records = extractor.extract_all(soup)

            elapsed = time.time() - start_time

            if not records:
                self.root.after(0, lambda: self._on_scrape_empty(url))
            else:
                default_file = derive_default_filename(url, ext="csv")
                export_data(records, default_file)
                self.root.after(0, lambda: self._on_scrape_success(records, default_file, elapsed))

        except Exception as err:
            self.root.after(0, lambda: self._on_scrape_error(err))
        finally:
            self.is_scraping = False
            self.root.after(0, self._reset_ui)

    def _on_scrape_success(self, records: list[dict], filename: str, elapsed: float):
        """Update table and status upon successful scrape."""
        self.current_records = records
        self.render_table(self.current_records)
        self.status_label.config(text=f"✓ Extracted {len(records)} records in {elapsed:.2f}s. Saved to '{filename}'.")

    def _on_scrape_empty(self, url: str):
        """Handle no records detected."""
        self.status_label.config(text="No structured data clusters found on page.")
        messagebox.showinfo("No Records", "No recurring item cards or metadata were detected on this page.")

    def _on_scrape_error(self, error: Exception):
        """Handle scrape failure."""
        self.status_label.config(text=f"Error: {error}")
        messagebox.showerror("Scraping Error", f"Extraction failed:\n{error}")

    def _reset_ui(self):
        """Restore buttons and progress indicators."""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_scrape.config(state="normal", text="🚀 SCRAPE DATA")
        self.status_badge.config(text="● READY", fg=THEME["success"])

    def render_table(self, records: list[dict]):
        """Populate treeview table."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(records, 1):
            title = row.get("title") or row.get("name") or "No Title"
            price = f"{row.get('currency', '')}{row.get('price', '')}" if "price" in row else "-"
            rating = f"{'*' * int(row['rating'])}" if "rating" in row and str(row["rating"]).isdigit() else str(row.get("rating", "-"))
            avail = row.get("availability") or ("In stock" if "stock_count" in row else "-")
            url = row.get("url", "")
            self.tree.insert("", tk.END, values=(i, title, price, rating, avail, url))

        self.table_title.config(text=f"EXTRACTED DATASETS ({len(records)})")

    def filter_table(self):
        """Filter table rows by live keyword."""
        query = self.filter_entry.get().strip().lower()
        if not query:
            self.render_table(self.current_records)
            return

        filtered = [
            r for r in self.current_records
            if any(query in str(v).lower() for v in r.values())
        ]
        self.render_table(filtered)
        self.table_title.config(text=f"EXTRACTED DATASETS ({len(filtered)} of {len(self.current_records)})")

    def save_csv(self):
        """Export current table to CSV via save dialog."""
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
        """Export current table to JSON via save dialog."""
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
        """Reset records and table."""
        self.current_records = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.table_title.config(text="EXTRACTED DATASETS (0)")
        self.status_label.config(text="Table cleared.")


def main():
    root = tk.Tk()
    app = ScrapeAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

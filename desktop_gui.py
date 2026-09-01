"""
ScrapeAgent - Native Desktop GUI Application.
A physical desktop application built with Python Tkinter and modern Obsidian/Cyan aesthetics.
Provides one-click URL scraping, live terminal activity logs, interactive table inspection,
and direct CSV/JSON exports without requiring a browser or web server.
"""
import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
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
# THEME: OBSIDIAN NIGHT & ELECTRIC CYAN
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
    "terminal_bg": "#040711",
    "terminal_fg": "#4ade80",
    "input_bg": "#0f172a",
}


class ScrapeAgentApp:
    """Native Windows Desktop GUI for ScrapeAgent."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ScrapeAgent · Autonomous Data Extraction Desktop")
        self.root.geometry("1100x780")
        self.root.minsize(920, 640)
        self.root.configure(bg=THEME["bg"])

        self.current_records = []
        self.is_scraping = False

        self._init_styles()
        self._init_ui()
        self.log("ScrapeAgent Desktop Engine initialized.")
        self.log(f"Working Directory: {PROJECT_ROOT}")

    def _init_styles(self):
        """Configure ttk styles for dark modern look."""
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview styling
        style.configure(
            "Treeview",
            background=THEME["surface"],
            foreground=THEME["text"],
            fieldbackground=THEME["surface"],
            rowheight=28,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["card"],
            foreground=THEME["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=6,
        )
        style.map(
            "Treeview",
            background=[("selected", THEME["border"])],
            foreground=[("selected", THEME["accent"])],
        )

        # Scrollbars
        style.configure("Vertical.TScrollbar", background=THEME["card"], troughcolor=THEME["surface"], borderwidth=0)
        style.configure("Horizontal.TScrollbar", background=THEME["card"], troughcolor=THEME["surface"], borderwidth=0)

    def _init_ui(self):
        t = THEME

        # 1. TOP HEADER / MASTHEAD
        self.header = tk.Frame(self.root, bg=t["surface"], padx=20, pady=14, highlightthickness=1, highlightbackground=t["border"])
        self.header.pack(fill="x", side="top")

        title_box = tk.Frame(self.header, bg=t["surface"])
        title_box.pack(side="left")

        tk.Label(title_box, text="ScrapeAgent", font=("Segoe UI", 18, "bold"), fg=t["accent"], bg=t["surface"]).pack(anchor="w")
        tk.Label(
            title_box,
            text="Autonomous Web Scraping & Structured Extraction Desktop",
            font=("Segoe UI", 9),
            fg=t["muted"],
            bg=t["surface"],
        ).pack(anchor="w")

        # Header right actions
        header_actions = tk.Frame(self.header, bg=t["surface"])
        header_actions.pack(side="right")

        self.status_pill = tk.Label(
            header_actions,
            text="● ENGINE READY",
            font=("Segoe UI", 9, "bold"),
            fg=t["success"],
            bg=t["subtle"],
            padx=12,
            pady=4,
        )
        self.status_pill.pack(side="left", padx=(0, 12))

        self.btn_open_folder = tk.Button(
            header_actions,
            text="📁 Open Folder",
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
        self.btn_open_folder.pack(side="left")

        # 2. INPUT CONTROL TOOLBAR
        self.control_frame = tk.Frame(self.root, bg=t["bg"], padx=20, pady=12)
        self.control_frame.pack(fill="x")

        # URL Input Bar
        url_box = tk.Frame(self.control_frame, bg=t["card"], padx=10, pady=8, highlightthickness=1, highlightbackground=t["border"])
        url_box.pack(fill="x", pady=(0, 10))

        tk.Label(url_box, text="TARGET URL:", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["card"]).pack(side="left", padx=(0, 10))

        self.url_entry = tk.Entry(
            url_box,
            font=("Segoe UI", 10),
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["accent"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=t["border"],
        )
        self.url_entry.insert(0, "https://books.toscrape.com/")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=4)
        self.url_entry.bind("<Return>", lambda e: self.start_scraping())

        # Scrape Action Button
        self.btn_scrape = tk.Button(
            url_box,
            text="🚀 SCRAPE URL",
            font=("Segoe UI", 10, "bold"),
            bg=t["accent"],
            fg=t["accent_text"],
            activebackground=t["accent_hover"],
            activeforeground=t["accent_text"],
            relief="flat",
            padx=18,
            pady=4,
            cursor="hand2",
            command=self.start_scraping,
        )
        self.btn_scrape.pack(side="right")

        # Secondary Options Toolbar
        opts_bar = tk.Frame(self.control_frame, bg=t["bg"])
        opts_bar.pack(fill="x")

        # Engine Selection Radio
        self.engine_var = tk.StringVar(value="http")
        tk.Label(opts_bar, text="Engine:", font=("Segoe UI", 9, "bold"), fg=t["muted"], bg=t["bg"]).pack(side="left", padx=(0, 6))

        r_http = tk.Radiobutton(
            opts_bar,
            text="HTTP (Fast)",
            variable=self.engine_var,
            value="http",
            bg=t["bg"],
            fg=t["text"],
            selectcolor=t["card"],
            activebackground=t["bg"],
            activeforeground=t["accent"],
            font=("Segoe UI", 9),
        )
        r_http.pack(side="left", padx=(0, 10))

        r_browser = tk.Radiobutton(
            opts_bar,
            text="Headless Browser (Playwright / Dynamic JS)",
            variable=self.engine_var,
            value="browser",
            bg=t["bg"],
            fg=t["text"],
            selectcolor=t["card"],
            activebackground=t["bg"],
            activeforeground=t["accent"],
            font=("Segoe UI", 9),
        )
        r_browser.pack(side="left", padx=(0, 20))

        # Quick Presets Dropdown
        tk.Label(opts_bar, text="Presets:", font=("Segoe UI", 9, "bold"), fg=t["muted"], bg=t["bg"]).pack(side="left", padx=(0, 6))
        self.preset_var = tk.StringVar(value="Books to Scrape")
        presets = ["Books to Scrape", "Quotes to Scrape", "Hacker News"]
        preset_dropdown = ttk.Combobox(opts_bar, values=presets, textvariable=self.preset_var, state="readonly", width=16)
        preset_dropdown.pack(side="left", padx=(0, 16))
        preset_dropdown.bind("<<ComboboxSelected>>", self.on_preset_change)

        # Batch Multi-page pipeline button
        self.btn_catalog = tk.Button(
            opts_bar,
            text="📚 Day 2 Multi-page Scraper",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["text"],
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self.start_catalog_scraper,
        )
        self.btn_catalog.pack(side="right", padx=(6, 0))

        # 3. PANED SPLIT VIEW (TABLE ON TOP, TERMINAL LOG ON BOTTOM)
        self.paned = tk.PanedWindow(self.root, orient="vertical", bg=t["border"], sashwidth=5, sashrelief="flat")
        self.paned.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # --- TOP PANE: RESULTS TABLE ---
        self.table_frame = tk.Frame(self.paned, bg=t["surface"], padx=14, pady=12)
        self.paned.add(self.table_frame, minsize=260)

        table_top_bar = tk.Frame(self.table_frame, bg=t["surface"])
        table_top_bar.pack(fill="x", pady=(0, 8))

        self.table_title = tk.Label(table_top_bar, text="EXTRACTED RECORDS (0)", font=("Segoe UI", 10, "bold"), fg=t["accent"], bg=t["surface"])
        self.table_title.pack(side="left")

        # Quick Filter search entry
        filter_box = tk.Frame(table_top_bar, bg=t["surface"])
        filter_box.pack(side="right")
        tk.Label(filter_box, text="Filter:", font=("Segoe UI", 9), fg=t["muted"], bg=t["surface"]).pack(side="left", padx=(0, 4))
        self.filter_entry = tk.Entry(filter_box, font=("Segoe UI", 9), bg=t["input_bg"], fg=t["text"], insertbackground=t["text"], relief="flat")
        self.filter_entry.pack(side="left", padx=(0, 8))
        self.filter_entry.bind("<KeyRelease>", lambda e: self.filter_table())

        # Treeview Table Container with Scrollbars
        tree_scroll_frame = tk.Frame(self.table_frame, bg=t["surface"])
        tree_scroll_frame.pack(fill="both", expand=True)

        self.tree_y_scroll = ttk.Scrollbar(tree_scroll_frame, orient="vertical", style="Vertical.TScrollbar")
        self.tree_y_scroll.pack(side="right", fill="y")

        self.tree_x_scroll = ttk.Scrollbar(tree_scroll_frame, orient="horizontal", style="Horizontal.TScrollbar")
        self.tree_x_scroll.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            tree_scroll_frame,
            yscrollcommand=self.tree_y_scroll.set,
            xscrollcommand=self.tree_x_scroll.set,
            columns=("idx", "title", "price", "rating", "availability", "url"),
            show="headings",
        )
        self.tree_y_scroll.config(command=self.tree.yview)
        self.tree_x_scroll.config(command=self.tree.xview)

        # Configure columns
        self.tree.heading("idx", text="#")
        self.tree.heading("title", text="Title / Headline")
        self.tree.heading("price", text="Price")
        self.tree.heading("rating", text="Rating")
        self.tree.heading("availability", text="Availability")
        self.tree.heading("url", text="Target URL")

        self.tree.column("idx", width=45, anchor="center")
        self.tree.column("title", width=380, anchor="w")
        self.tree.column("price", width=90, anchor="center")
        self.tree.column("rating", width=80, anchor="center")
        self.tree.column("availability", width=110, anchor="center")
        self.tree.column("url", width=300, anchor="w")

        self.tree.pack(fill="both", expand=True)

        # Table Bottom Actions Bar
        tbl_bottom = tk.Frame(self.table_frame, bg=t["surface"], pady=8)
        tbl_bottom.pack(fill="x")

        self.btn_export_csv = tk.Button(
            tbl_bottom,
            text="💾 Export to CSV",
            font=("Segoe UI", 9, "bold"),
            bg=t["card"],
            fg=t["text"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.export_csv_action,
        )
        self.btn_export_csv.pack(side="left", padx=(0, 8))

        self.btn_export_json = tk.Button(
            tbl_bottom,
            text="💾 Export to JSON",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["text"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.export_json_action,
        )
        self.btn_export_json.pack(side="left", padx=(0, 8))

        self.btn_clear = tk.Button(
            tbl_bottom,
            text="✕ Clear Table",
            font=("Segoe UI", 9),
            bg=t["card"],
            fg=t["muted"],
            activebackground=t["border"],
            activeforeground=t["text"],
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.clear_table,
        )
        self.btn_clear.pack(side="left")

        # --- BOTTOM PANE: LIVE TERMINAL ACTIVITY LOG ---
        self.log_frame = tk.Frame(self.paned, bg=t["terminal_bg"], padx=12, pady=10)
        self.paned.add(self.log_frame, minsize=180)

        log_hdr = tk.Frame(self.log_frame, bg=t["terminal_bg"])
        log_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(log_hdr, text="TERMINAL ACTIVITY & EXTRACTION LOG", font=("Consolas", 9, "bold"), fg=t["muted"], bg=t["terminal_bg"]).pack(side="left")

        btn_clear_log = tk.Button(
            log_hdr,
            text="Clear Log",
            font=("Segoe UI", 8),
            bg=t["card"],
            fg=t["muted"],
            relief="flat",
            padx=6,
            pady=1,
            cursor="hand2",
            command=lambda: self.log_text.delete("1.0", tk.END),
        )
        btn_clear_log.pack(side="right")

        self.log_text = tk.Text(
            self.log_frame,
            font=("Consolas", 9),
            bg=t["terminal_bg"],
            fg=t["terminal_fg"],
            insertbackground=t["terminal_fg"],
            relief="flat",
            wrap="word",
            height=8,
        )
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview, style="Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=self.log_scroll.set)

        self.log_scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

        # 4. STATUS BAR
        self.status_bar = tk.Frame(self.root, bg=t["surface"], padx=20, pady=6, highlightthickness=1, highlightbackground=t["border"])
        self.status_bar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(self.status_bar, text="Ready to scrape.", font=("Segoe UI", 9), fg=t["muted"], bg=t["surface"])
        self.status_label.pack(side="left")

        self.stats_label = tk.Label(self.status_bar, text="0 records in memory", font=("Segoe UI", 9), fg=t["accent"], bg=t["surface"])
        self.stats_label.pack(side="right")

    # -------------------------------------------------------------------------
    # LOGIC & WORKERS
    # -------------------------------------------------------------------------
    def log(self, message: str):
        """Append timestamped log entry to the native terminal text widget."""
        now = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now}] {message}\n"
        self.log_text.insert(tk.END, formatted)
        self.log_text.see(tk.END)

    def on_preset_change(self, event=None):
        """Update URL entry based on selected preset."""
        choice = self.preset_var.get()
        urls = {
            "Books to Scrape": "https://books.toscrape.com/",
            "Quotes to Scrape": "https://quotes.toscrape.com/",
            "Hacker News": "https://news.ycombinator.com/",
        }
        if choice in urls:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, urls[choice])

    def open_output_folder(self):
        """Open the application directory in Windows File Explorer."""
        path = os.path.abspath(PROJECT_ROOT)
        self.log(f"Opening File Explorer: {path}")
        if sys.platform == "win32":
            os.system(f'explorer "{path}"')
        else:
            messagebox.showinfo("Folder Location", f"Application files location:\n{path}")

    def start_scraping(self):
        """Validate input and trigger background worker thread."""
        if self.is_scraping:
            messagebox.showwarning("In Progress", "A scraping operation is already running.")
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
        self.status_pill.config(text="● SCRAPING ACTIVE", fg=THEME["warning"])
        self.status_label.config(text=f"Navigating to {url}...")

        threading.Thread(target=self._scrape_thread, args=(url, use_browser), daemon=True).start()

    def _scrape_thread(self, url: str, use_browser: bool):
        """Thread worker performing fetch, clean, and extraction."""
        start_time = time.time()
        self.log(f"Connecting to: {url} [{'Playwright Browser' if use_browser else 'HTTP Client'}]")

        try:
            if use_browser:
                from core.browser_fetcher import fetch_page_browser
                self.log("Launching Chromium headless instance and waiting for DOM rendering...")
                raw_html = fetch_page_browser(url)
                size_kb = len(raw_html.encode("utf-8")) // 1024
                self.log(f"DOM rendered successfully: {size_kb} KB received.")
            else:
                resp = fetch_page(url)
                raw_html = resp.text
                size_kb = len(resp.content) // 1024
                self.log(f"HTTP Status {resp.status_code} OK: {size_kb} KB received.")

            self.log("Sanitizing DOM markup and stripping non-semantic noise tags...")
            soup = clean_html(raw_html)

            # Check bot wall
            block_reason = check_bot_protection(soup)
            if block_reason:
                self.log(f"[WARNING] Anti-Bot Challenge Screen Detected: {block_reason}")
                if not use_browser:
                    self.log("[HINT] Switch engine to 'Headless Browser' to bypass client-side script blocks.")

            self.log("Universal Extractor searching for recurring DOM structures...")
            extractor = UniversalExtractor(base_url=url)
            records = extractor.extract_all(soup)

            elapsed = time.time() - start_time

            if not records:
                self.log("[-] No recurring data records or metadata identified on this page.")
                self.root.after(0, lambda: messagebox.showinfo("No Records", "No structured items could be detected on this page."))
            else:
                self.log(f"[✓] Successfully extracted {len(records)} structured items in {elapsed:.2f}s!")
                # Auto-save to default CSV
                default_csv = derive_default_filename(url, ext="csv")
                saved_path = export_data(records, default_csv)
                self.log(f"[✓] Dataset auto-saved to: {saved_path}")

                self.root.after(0, self._update_results, records, default_csv)

        except Exception as err:
            self.log(f"[ERROR] Extraction failed: {err}")
            self.root.after(0, lambda: messagebox.showerror("Scraping Error", f"Extraction failed:\n{err}"))
        finally:
            self.is_scraping = False
            self.root.after(0, self._reset_scrape_ui)

    def _update_results(self, records: list[dict], saved_filename: str):
        """Populate treeview with extracted data."""
        self.current_records = records
        self.populate_treeview(self.current_records)
        self.status_label.config(text=f"Extracted {len(records)} items. Saved to '{saved_filename}'.")
        self.stats_label.config(text=f"{len(records)} records in memory")

    def _reset_scrape_ui(self):
        """Reset buttons and status pills after extraction."""
        self.btn_scrape.config(state="normal", text="🚀 SCRAPE URL")
        self.status_pill.config(text="● ENGINE READY", fg=THEME["success"])

    def populate_treeview(self, records: list[dict]):
        """Render records into Treeview table."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(records, 1):
            title = row.get("title") or row.get("name") or "No Title"
            price = f"{row.get('currency', '')}{row.get('price', '')}" if "price" in row else "-"
            rating = f"{'*' * int(row['rating'])}" if "rating" in row and str(row["rating"]).isdigit() else str(row.get("rating", "-"))
            avail = row.get("availability") or ("In stock" if "stock_count" in row else "-")
            url = row.get("url", "")
            self.tree.insert("", tk.END, values=(i, title, price, rating, avail, url))

        self.table_title.config(text=f"EXTRACTED RECORDS ({len(records)})")

    def filter_table(self):
        """Filter table rows dynamically based on the search box."""
        query = self.filter_entry.get().strip().lower()
        if not query:
            self.populate_treeview(self.current_records)
            return

        filtered = [
            r for r in self.current_records
            if any(query in str(v).lower() for v in r.values())
        ]
        self.populate_treeview(filtered)
        self.table_title.config(text=f"EXTRACTED RECORDS ({len(filtered)} of {len(self.current_records)})")

    def export_csv_action(self):
        """Prompt file dialog and export to custom CSV."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Save Extracted Records to CSV",
        )
        if file_path:
            export_data(self.current_records, file_path)
            self.log(f"Exported {len(self.current_records)} records to CSV: {file_path}")
            messagebox.showinfo("Export Successful", f"Saved {len(self.current_records)} records to:\n{file_path}")

    def export_json_action(self):
        """Prompt file dialog and export to JSON."""
        if not self.current_records:
            messagebox.showwarning("Empty", "No records available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Extracted Records to JSON",
        )
        if file_path:
            export_data(self.current_records, file_path)
            self.log(f"Exported {len(self.current_records)} records to JSON: {file_path}")
            messagebox.showinfo("Export Successful", f"Saved {len(self.current_records)} records to:\n{file_path}")

    def clear_table(self):
        """Clear current memory records and Treeview."""
        self.current_records = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.table_title.config(text="EXTRACTED RECORDS (0)")
        self.stats_label.config(text="0 records in memory")
        self.log("Memory dataset cleared.")

    def start_catalog_scraper(self):
        """Run Day 2 multi-page scraper inside background thread."""
        if self.is_scraping:
            messagebox.showwarning("In Progress", "Another scraping task is currently running.")
            return

        self.is_scraping = True
        self.status_pill.config(text="● BATCH PIPELINE", fg=THEME["warning"])
        self.btn_catalog.config(state="disabled")

        def run_batch():
            self.log("Starting Day 2 Multi-Page Catalog Scraper (pages 1-2)...")
            try:
                from scrape_all_books import run_full_catalog_scraper
                books = run_full_catalog_scraper(max_pages=2, output_csv="all_books.csv")
                self.log(f"[✓] Day 2 pipeline completed: {len(books)} books scraped into 'all_books.csv'.")
                self.root.after(0, lambda: self._update_results(books, "all_books.csv"))
            except Exception as err:
                self.log(f"[ERROR] Multi-page crawler failed: {err}")
            finally:
                self.is_scraping = False
                self.root.after(0, lambda: self.btn_catalog.config(state="normal"))
                self.root.after(0, self._reset_scrape_ui)

        threading.Thread(target=run_batch, daemon=True).start()


def main():
    root = tk.Tk()
    app = ScrapeAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

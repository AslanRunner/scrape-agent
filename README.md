# ScrapeAgent

A lightweight desktop and command-line tool to extract structured data (tables, cards, listings) from any webpage into CSV or JSON format.

---

## Features

- **Automatic Pattern Extraction:** Automatically detects repeating structures (products, articles, lists, tables) without requiring manual CSS selectors or XPath rules.
- **Dual Scraping Engines:**
  - **HTTP Engine:** Fast, lightweight requests engine for standard static HTML pages.
  - **Browser Engine (Playwright):** Full Chromium rendering for dynamic, client-side JavaScript (SPA) pages.
- **Dark & Light Themes:** Modern Blue & Black interface with a single-click mode toggle.
- **Live Table & Search:** View extracted records in a responsive table with instant search and filtering.
- **One-Click Export:** Export data directly to `.csv` or `.json`.
- **CLI & GUI:** Run via an intuitive desktop GUI or through direct command-line commands.

---

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AslanRunner/scrape-agent.git
cd scrape-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. *(Optional - for dynamic JavaScript pages)*:
```bash
playwright install chromium
```

---

## Usage

### 1. Desktop GUI
Run `ScrapeAgent.bat` (or execute via terminal):

```bash
python desktop_gui.py
```

### 2. Command-Line Interface (CLI)

**Interactive Menu:**
```bash
python agent.py
```

**Direct Command Execution:**
```bash
# Scrape static page using HTTP engine and export to CSV
python agent.py --url "https://quotes.toscrape.com/" --output "quotes.csv"

# Scrape dynamic JavaScript page using headless browser
python agent.py --url "https://example.com" --browser --output "data.json"
```

---

## Project Structure

```text
scrape-agent/
├── desktop_gui.py      # Desktop GUI application (CustomTkinter)
├── agent.py            # Command-line interface and interactive menu
├── config.py           # Configuration settings
├── ScrapeAgent.bat     # Windows desktop launcher
├── run.bat             # Terminal launcher
├── requirements.txt    # Python dependencies
├── assets/             # Icons and visual assets
├── output/             # Extracted datasets directory
└── core/               # Core extraction modules
    ├── fetcher.py      # HTTP request client
    ├── browser_fetcher.py # Headless Chromium client (Playwright)
    ├── cleaner.py      # HTML cleanup and sanitization
    ├── extractor.py    # Pattern discovery and data extraction engine
    └── exporter.py     # CSV and JSON exporter
```

---

## License

This project is licensed under the [MIT](LICENSE) License.

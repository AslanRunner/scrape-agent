"""
ScrapeAgent - Desktop Local Application.
Command-line interface for universal web scraping, dynamic browser rendering,
and local dataset search & analytics.
"""
import argparse
import os
import re
import subprocess
import sys
from urllib.parse import urlparse

# Force UTF-8 output in Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.extractor import UniversalExtractor
from core.exporter import export_data

BANNER = r"""
======================================================================
   _____                               ___                    _   
  / ___/______________ _____  ___     /   | ____ ____  ____  / /_ 
  \__ \/ ___/ ___/ __ `/ __ \/ _ \   / /| |/ __ `/ _ \/ __ \/ __/ 
 ___/ / /__/ /  / /_/ / /_/ /  __/  / ___ / /_/ /  __/ / / / /_   
/____/\___/_/   \__,_/ .___/\___/  /_/  |_\__, /\___/_/ /_/\__/   
                    /_/                  /____/                   
       ScrapeAgent - Local Desktop Scraping Application
======================================================================
"""

URL_REGEX = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    """Ensure URL has an http/https scheme and is stripped of whitespace."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def is_valid_url(url: str) -> bool:
    """Validate that the provided string is a syntactically valid HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    normalized = normalize_url(url)
    try:
        parsed = urlparse(normalized)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        return bool(URL_REGEX.match(normalized))
    except Exception:
        return False


def derive_default_filename(url: str, ext: str = "csv") -> str:
    """Derive a clean, readable default filename based on the URL domain and path."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]", "_", domain)
    path_slug = re.sub(r"[^a-zA-Z0-9]", "_", parsed.path.strip("/"))
    if path_slug:
        slug = f"{slug}_{path_slug}"
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"{slug[:45]}.{ext}"


def check_bot_protection(soup) -> str | None:
    """Detect common anti-bot challenge screens (Cloudflare, reCAPTCHA, Datadome)."""
    title = soup.find("title")
    title_text = title.get_text().lower() if title else ""
    if any(sig in title_text for sig in ["recaptcha", "checking your browser", "just a moment...", "cloudflare"]):
        return "Cloudflare / reCAPTCHA Challenge (Bot Protection)"
    if any(sig in title_text for sig in ["attention required", "access denied", "security check", "robot or human?"]):
        return "Access Denied / Anti-Bot Security Block"
    return None


def run_agent(url: str, output_path: str | None = None, use_browser: bool = False) -> None:
    """Execute scraping pipeline on target URL and export dataset."""
    if not is_valid_url(url):
        print(f"\n[!] Invalid URL provided: '{url}'")
        print("[i] Please supply a valid address (e.g. 'https://books.toscrape.com' or 'example.com').")
        return

    url = normalize_url(url)
    if not output_path:
        output_path = derive_default_filename(url, ext="csv")

    mode_label = "Headless Browser (Playwright)" if use_browser else "HTTP Engine"
    print(f"\n[+] Navigating to: {url} [{mode_label}]")

    try:
        # Step 1: Fetch
        if use_browser:
            print("[+] Launching Chromium and executing client scripts...")
            from core.browser_fetcher import fetch_page_browser
            html_text = fetch_page_browser(url)
            print(f"[+] DOM rendered successfully ({len(html_text) // 1024} KB markup)")
        else:
            response = fetch_page(url)
            size_kb = len(response.content) // 1024
            print(f"[+] Status {response.status_code} OK ({size_kb} KB received)")
            html_text = response.text

        # Step 2: Clean & Parse
        print("[+] Sanitizing HTML and stripping noise tags...")
        soup = clean_html(html_text)

        # Check for Bot Protection / Cloudflare Block
        block_reason = check_bot_protection(soup)
        if block_reason:
            print(f"\n[!] Anti-Bot Protection Detected: {block_reason}")
            print("[i] The website blocked automated Python requests and served a verification screen.")
            if not use_browser:
                print("[i] Hint: Try running with the '--browser' option to render with a real browser engine.")
            print(f"[i] Note: '{output_path}' was not generated because the request was blocked.")
            return

        # Step 3: Extract
        print("[+] Universal Extractor analyzing DOM structure...")
        extractor = UniversalExtractor(base_url=url)
        results = extractor.extract_all(soup)

        if not results:
            print("\n[-] No structured data could be extracted.")
            if not use_browser:
                print("[i] The page might be a Client-Side Rendered (SPA) app where content is injected via JavaScript.")
                print("[i] Hint: Try running with '--browser' to execute client scripts before parsing.")
            print(f"[i] Note: '{output_path}' was not created because no records were found.")
            return

        print(f"[+] Discovered {len(results)} structured items.\n")

        # Preview first 5 items
        print("--- Record Preview ---")
        for i, item in enumerate(results[:5], 1):
            title = item.get("title", "No Title")
            disp_title = title if len(title) <= 48 else title[:45] + "..."
            price_info = f"{item.get('currency', '')}{item.get('price', '')}" if "price" in item else ""
            print(f"  {i:>2}. {disp_title:<50} {price_info}")
            if "url" in item:
                print(f"      Link: {item['url']}")

        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more items.")

        # Step 4: Export
        saved_file = export_data(results, output_path)
        print(f"\n[+] Results successfully exported to:")
        print(f"    {saved_file}")

    except Exception as e:
        print(f"\n[!] Error during scraping: {e}")


def open_output_folder():
    """Open current directory in Windows File Explorer."""
    current_dir = os.path.abspath(".")
    print(f"\n[+] Opening folder in File Explorer: {current_dir}")
    if sys.platform == "win32":
        os.system(f'explorer "{current_dir}"')
    else:
        print(f"[i] Working directory: {current_dir}")


def interactive_desktop_app():
    """Main interactive desktop application loop."""
    while True:
        print(BANNER)
        print("Menu Options:")
        print("  1. Scrape a custom URL (HTTP Engine - Fast)")
        print("  2. Scrape a custom URL (Headless Browser - Dynamic JS / Playwright)")
        print("  3. Run Book Catalog Scraper (Day 2 Multi-page & Detail pipeline)")
        print("  4. Search & Analyze Scraped Datasets (Day 3 REPL Engine)")
        print("  5. Open Output Folder in File Explorer")
        print("  6. Exit")

        choice = input("\nSelect an option (1-6) [1]: ").strip() or "1"

        if choice == "1" or choice == "2":
            use_browser = choice == "2"
            while True:
                raw_url = input("\nEnter target URL to scrape (or 'cancel'): ").strip()
                if not raw_url or raw_url.lower() == "cancel":
                    print("Operation cancelled.")
                    break
                if is_valid_url(raw_url):
                    url = normalize_url(raw_url)
                    auto_name = derive_default_filename(url, ext="csv")
                    out_input = input(f"Output CSV/JSON filename [press Enter for '{auto_name}']: ").strip()
                    output_file = out_input if out_input else auto_name
                    run_agent(url, output_path=output_file, use_browser=use_browser)
                    break
                print(f"[-] Invalid URL format: '{raw_url}'. Example: 'books.toscrape.com'")

            input("\nPress Enter to return to menu...")

        elif choice == "3":
            from scrape_all_books import run_full_catalog_scraper
            pages_input = input("\nEnter number of pages to scrape (1-50) [default: 2]: ").strip() or "2"
            try:
                pages_val = int(pages_input)
            except ValueError:
                pages_val = 2
            run_full_catalog_scraper(max_pages=pages_val, output_csv="all_books.csv")
            input("\nPress Enter to return to menu...")

        elif choice == "4":
            from search_books import load_dataset, run_repl, CSV_DEFAULT_FILE
            target_csv = input(f"\nDataset CSV to load [default: '{CSV_DEFAULT_FILE}']: ").strip() or CSV_DEFAULT_FILE
            df = load_dataset(target_csv)
            run_repl(df)
            input("\nPress Enter to return to menu...")

        elif choice == "5":
            open_output_folder()
            input("\nPress Enter to return to menu...")

        elif choice == "6":
            print("\nGoodbye!")
            break
        else:
            print("Invalid option selected. Please choose 1-6.")


def main():
    parser = argparse.ArgumentParser(description="ScrapeAgent - Desktop Scraping Application")
    parser.add_argument("--url", "-u", type=str, help="Target URL to scrape directly")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file path (.csv or .json)")
    parser.add_argument("--browser", "-b", action="store_true", help="Render dynamic JavaScript/SPA pages using headless browser (Playwright)")
    parser.add_argument("--demo", action="store_true", help="Run the books.toscrape.com demo scraper")

    args = parser.parse_args()

    if args.demo:
        from examples.book_scraper import main as run_book_demo
        run_book_demo()
    elif args.url:
        print(BANNER)
        run_agent(args.url, output_path=args.output, use_browser=args.browser)
    else:
        interactive_desktop_app()


if __name__ == "__main__":
    main()

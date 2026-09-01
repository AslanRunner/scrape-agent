"""
ScrapeAgent - Autonomous Web Scraping & Intelligent Extraction Agent.
CLI Entry point for universal URL scraping and structured data extraction.
"""
import argparse
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
from examples.book_scraper import scrape_books


BANNER = r"""
   _____                               ___                    _   
  / ___/______________ _____  ___     /   | ____ ____  ____  / /_ 
  \__ \/ ___/ ___/ __ `/ __ \/ _ \   / /| |/ __ `/ _ \/ __ \/ __/ 
 ___/ / /__/ /  / /_/ / /_/ /  __/  / ___ / /_/ /  __/ / / / /_   
/____/\___/_/   \__,_/ .___/\___/  /_/  |_\__, /\___/_/ /_/\__/   
                    /_/                  /____/                   
          Intelligent & Autonomous Web Scraping Agent
"""


def is_valid_url(url: str) -> bool:
    """Validate URL scheme and network location."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def run_agent(url: str, output_path: str = "scraped_data.csv") -> None:
    """Execute scraping pipeline on any target URL."""
    print(f"\n[+] Agent navigating to: {url}")

    try:
        # Step 1: Fetch
        response = fetch_page(url)
        size_kb = len(response.content) // 1024
        print(f"[✓] Status {response.status_code} OK ({size_kb} KB received)")

        # Step 2: Clean & Parse
        print("[+] Sanitizing HTML & stripping noise...")
        soup = clean_html(response.text)

        # Step 3: Extract
        print("[+] Universal Extractor analyzing DOM structure...")
        extractor = UniversalExtractor(base_url=url)
        results = extractor.extract_all(soup)

        if not results:
            print("[-] No repeating data cards detected automatically.")
            print("[i] Site may require JavaScript rendering or custom selector rules.")
            return

        print(f"[✓] Discovered {len(results)} structured items!\n")

        # Preview first 5 items
        print("--- Previewing Extracted Records ---")
        for i, item in enumerate(results[:5], 1):
            title = item.get("title", "No Title")
            disp_title = title if len(title) <= 50 else title[:47] + "..."
            price_info = f"{item.get('currency', '')}{item.get('price', '')}" if "price" in item else ""
            print(f"  {i:>2}. {disp_title:<52} {price_info}")
            if "url" in item:
                print(f"      Link: {item['url']}")

        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more items.")

        # Step 4: Export
        saved_file = export_data(results, output_path)
        print(f"\n[✓] Results successfully exported to: {saved_file}")

    except Exception as e:
        print(f"\n[!] Error during scraping: {e}")


def interactive_mode():
    """Start interactive command-line agent session."""
    print(BANNER)
    print("Welcome to ScrapeAgent! You can scrape any URL or run preset scenarios.")
    print("1. Scrape a custom URL (Universal Pattern Discovery)")
    print("2. Run Book Catalog Scraper (books.toscrape.com demo)")
    print("3. Exit")

    choice = input("\nSelect an option (1-3) [1]: ").strip() or "1"

    if choice == "2":
        from examples.book_scraper import main as run_book_demo
        run_book_demo()
    elif choice == "3":
        print("Goodbye!")
        sys.exit(0)
    else:
        url = input("\nEnter target URL to scrape: ").strip()
        if not url:
            print("[-] No URL provided. Exiting.")
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        output = input("Output file path (default: scraped_data.csv): ").strip() or "scraped_data.csv"
        run_agent(url, output)


def main():
    parser = argparse.ArgumentParser(description="ScrapeAgent - Autonomous Web Scraping Agent")
    parser.add_argument("--url", "-u", type=str, help="Target URL to scrape")
    parser.add_argument("--output", "-o", type=str, default="scraped_data.csv", help="Output file path (.csv or .json)")
    parser.add_argument("--demo", action="store_true", help="Run the books.toscrape.com demo scraper")

    args = parser.parse_args()

    if args.demo:
        from examples.book_scraper import main as run_book_demo
        run_book_demo()
    elif args.url:
        print(BANNER)
        run_agent(args.url, args.output)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()

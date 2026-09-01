"""
Web Scraping with BeautifulSoup: Day 2 - Multi-Page Scraping with Pagination.
Scrapes the full catalog of 1,000 books across 50 pages from books.toscrape.com,
enriching each book with rich details (UPC, stock count, category, description)
from its individual detail page.
"""
import argparse
import csv
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# --- Configuration Settings ---
BASE_URL = "https://books.toscrape.com/"
CSV_FILENAME = "all_books.csv"
REQUEST_DELAY = 0.2  # 200ms polite delay between requests
MAX_PAGES = None      # Set to integer (e.g. 2 or 3) for quick tests, or None for all 50 pages

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (Python Scraper)"
}

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

FIELDNAMES = [
    "title",
    "price",
    "rating",
    "availability",
    "stock_count",
    "category",
    "upc",
    "description",
    "url",
]


def fetch_page(url: str, retries: int = 2) -> BeautifulSoup | None:
    """
    Fetch a web page safely with headers, timeout, encoding fix, and retry handling.
    Returns BeautifulSoup object or None if the request failed.
    """
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            response.raise_for_status()
            response.encoding = "utf-8"
            return BeautifulSoup(response.text, "html.parser")
        except Exception:
            if attempt < retries:
                time.sleep(0.5)
            else:
                return None
    return None


def find_next_url(soup: BeautifulSoup, current_url: str) -> str | None:
    """Return the absolute URL of the next page, or None if this is the last page."""
    next_li = soup.find("li", class_="next")
    if next_li is None:
        return None
    next_a = next_li.find("a")
    if not next_a or "href" not in next_a.attrs:
        return None
    return urljoin(current_url, next_a["href"])


def scrape_listing_card(card, current_url: str) -> dict:
    """Extract listing-level data from a single product_pod card."""
    # 1. Full Title & Relative URL
    title_link = card.find("h3").find("a")
    title = title_link.get("title", "").strip() or title_link.get_text(strip=True)
    detail_url = urljoin(current_url, title_link.get("href", ""))

    # 2. Price
    price_tag = card.find("p", class_="price_color")
    price_text = price_tag.get_text() if price_tag else "0"
    clean_price = price_text.replace("£", "").replace("Â", "").strip()
    try:
        price = float(clean_price)
    except ValueError:
        price = 0.0

    # 3. Star Rating
    rating_tag = card.find("p", class_="star-rating")
    rating_classes = rating_tag.get("class", []) if rating_tag else []
    rating_word = next((c for c in rating_classes if c != "star-rating"), "Zero")
    rating = RATING_MAP.get(rating_word, 0)

    # 4. Stock Availability
    avail_tag = card.find("p", class_="instock availability")
    availability = avail_tag.get_text(strip=True) if avail_tag else "Unknown"

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "availability": availability,
        "url": detail_url,
    }


def extract_upc(soup: BeautifulSoup) -> str:
    """Extract Universal Product Code from the product details table."""
    table = soup.find("table", class_="table-striped")
    if table:
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and th.get_text(strip=True) == "UPC":
                return td.get_text(strip=True)
    return ""


def extract_stock_count(soup: BeautifulSoup) -> int | None:
    """Extract exact numeric stock availability (e.g. '(22 available)')."""
    table = soup.find("table", class_="table-striped")
    if table:
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td and th.get_text(strip=True) == "Availability":
                text = td.get_text(strip=True)
                match = re.search(r"\((\d+)\s+available\)", text)
                if match:
                    return int(match.group(1))
    return None


def extract_category(soup: BeautifulSoup) -> str:
    """Extract book category from the breadcrumb navigation bar."""
    breadcrumbs = soup.find("ul", class_="breadcrumb")
    if breadcrumbs:
        lis = breadcrumbs.find_all("li")
        if len(lis) >= 3:
            return lis[2].get_text(strip=True)
    return "Default"


def extract_description(soup: BeautifulSoup) -> str:
    """Extract full book description located after #product_description header."""
    header = soup.find("div", id="product_description")
    if header:
        desc_p = header.find_next_sibling("p")
        if desc_p:
            return desc_p.get_text(strip=True)
    return ""


def enrich_with_details(book: dict) -> dict:
    """Fetch the book's detail page and pull richer fields (UPC, stock, category, description)."""
    soup = fetch_page(book["url"])
    time.sleep(REQUEST_DELAY)

    if soup is None:
        book.update({
            "stock_count": None,
            "category": "Unknown",
            "upc": "",
            "description": "",
        })
        return book

    book["upc"] = extract_upc(soup)
    book["stock_count"] = extract_stock_count(soup)
    book["category"] = extract_category(soup)
    book["description"] = extract_description(soup)
    return book


def save_books_to_csv(books: list[dict], filename: str = CSV_FILENAME) -> None:
    """Write all scraped books to a single CSV file with proper UTF-8 encoding."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(books)


def run_full_catalog_scraper(max_pages: int | None = MAX_PAGES, output_csv: str = CSV_FILENAME) -> list[dict]:
    """Execute complete pagination loop across catalog pages and detail pages."""
    start_time = time.time()
    url = BASE_URL
    page_number = 0
    all_books = []

    print("=" * 65)
    print("BOOK SCRAPER - Day 2: Multi-Page Scraping with Pagination")
    print("=" * 65)

    while url:
        page_number += 1
        print(f"\nPage {page_number} of ~50: {url}")

        soup = fetch_page(url)
        time.sleep(REQUEST_DELAY)

        if soup is None:
            print(f"  [!] Failed to load page {page_number}. Stopping pagination.")
            break

        cards = soup.find_all("article", class_="product_pod")
        print(f"  ✓ {len(cards)} books found")

        for book_idx, card in enumerate(cards, start=1):
            book = scrape_listing_card(card, url)
            # Enrich with detail page fields
            book = enrich_with_details(book)
            all_books.append(book)

            # Display progress matching Day 2 terminal format
            disp_title = book["title"] if len(book["title"]) <= 38 else book["title"][:35] + "..."
            price_str = f"£{book['price']:.2f}"
            stock_label = f"({book['stock_count']})" if book["stock_count"] is not None else "(?)"

            print(f" {book_idx:>2}/{len(cards)} {disp_title:<42} {price_str:<8} {book['availability']}")
            print(f"      {stock_label} {book['category']}")

        # Check for next page
        url = find_next_url(soup, url)

        # Respect max_pages limit if set
        if max_pages is not None and page_number >= max_pages:
            print(f"\n[i] Reached test page limit ({max_pages} pages).")
            break

    # Save to CSV
    save_books_to_csv(all_books, output_csv)
    elapsed = time.time() - start_time

    # Final Summary Report
    print("\n" + "=" * 65)
    print(f"✓ Scraped {len(all_books)} books across {page_number} pages in {elapsed:.1f}s")
    print(f"✓ Saved: {output_csv}")
    print("=" * 65)

    if all_books:
        avg_price = sum(b["price"] for b in all_books) / len(all_books)
        categories = {b["category"] for b in all_books}
        in_stock_sum = sum(b["stock_count"] or 0 for b in all_books)

        print("\nSummary:")
        print(f"  Total Books:       {len(all_books)}")
        print(f"  Pages Crawled:     {page_number}")
        print(f"  Average Price:     £{avg_price:.2f}")
        print(f"  Unique Categories: {len(categories)}")
        print(f"  Total Units Stock: {in_stock_sum}")

    return all_books


def main():
    parser = argparse.ArgumentParser(description="Day 2 - Multi-Page Book Scraper with Pagination")
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=MAX_PAGES,
        help="Maximum pages to scrape (default: all 50 pages). Set e.g. -p 2 for quick testing.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=CSV_FILENAME,
        help=f"Output CSV path (default: {CSV_FILENAME})",
    )
    args = parser.parse_args()

    run_full_catalog_scraper(max_pages=args.pages, output_csv=args.output)


if __name__ == "__main__":
    main()

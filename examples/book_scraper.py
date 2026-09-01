"""
Book Scraper Example for ScrapeAgent.
Demonstrates extracting catalog data from books.toscrape.com using ScrapeAgent core components.
"""
import os
import sys
from urllib.parse import urljoin

# Add parent directory to sys.path to enable imports from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.exporter import export_data

TARGET_URL = "https://books.toscrape.com/"
OUTPUT_CSV = "books.csv"

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def scrape_books(url: str = TARGET_URL) -> list[dict]:
    """Scrape 20 books from the target catalog page."""
    response = fetch_page(url)
    soup = clean_html(response.text)
    cards = soup.find_all("article", class_="product_pod")

    books = []
    for card in cards:
        # Full title
        title_link = card.find("h3").find("a")
        title = title_link["title"].strip()

        # Price
        price_text = card.find("p", class_="price_color").get_text()
        clean_price = price_text.replace("£", "").replace("Â", "").strip()
        price = float(clean_price)

        # Rating
        rating_classes = card.find("p", class_="star-rating")["class"]
        rating_word = [c for c in rating_classes if c != "star-rating"][0]
        rating = RATING_MAP.get(rating_word, 0)

        # Availability
        avail_tag = card.find("p", class_="instock availability")
        availability = avail_tag.get_text(strip=True) if avail_tag else "Unknown"

        # Detail URL
        full_url = urljoin(url, title_link["href"])

        books.append({
            "title": title,
            "price": price,
            "rating": rating,
            "availability": availability,
            "url": full_url,
        })

    return books


def main():
    print("=" * 60)
    print("ScrapeAgent Example: Book Catalog Scraper")
    print("=" * 60)

    print(f"\n[+] Fetching: {TARGET_URL}")
    books = scrape_books(TARGET_URL)
    print(f"[✓] Successfully parsed {len(books)} books.")

    for i, b in enumerate(books, 1):
        disp_title = b["title"] if len(b["title"]) <= 37 else b["title"][:27] + "..."
        stars = "*" * b["rating"]
        print(f"  {i:>2}. {disp_title:<40} £{b['price']:.2f}   {stars}")
        print(f"     {b['availability']}")

    export_path = export_data(books, OUTPUT_CSV)
    print(f"\n[✓] Exported to: {export_path}")


if __name__ == "__main__":
    main()

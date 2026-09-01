"""Universal data extractor engine for ScrapeAgent."""
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup, Tag


class UniversalExtractor:
    """
    Intelligent extractor capable of identifying repeating item patterns
    (products, articles, listings) across any website without strict site-specific scripts.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

    def find_repeating_items(self, soup: BeautifulSoup) -> list[Tag]:
        """
        Heuristically locate repeating item cards or list containers.
        """
        # 1. Look for explicit semantic tags first
        articles = soup.find_all("article")
        if len(articles) >= 3:
            return articles

        # 2. Check for common class naming conventions
        common_card_patterns = re.compile(r"(product|item|card|post|listing|entry|result|book)", re.I)
        candidate_containers = soup.find_all(["div", "li"], class_=common_card_patterns)
        if len(candidate_containers) >= 3:
            # Group by class name signature to find the dominant repeating pattern
            class_counts = {}
            for tag in candidate_containers:
                cls_key = " ".join(sorted(tag.get("class", [])))
                class_counts[cls_key] = class_counts.get(cls_key, 0) + 1

            best_class = max(class_counts, key=class_counts.get)
            if class_counts[best_class] >= 3:
                return [tag for tag in candidate_containers if " ".join(sorted(tag.get("class", []))) == best_class]

        # 3. Fallback: Repeated links with headings
        headings = soup.find_all(["h2", "h3", "h4"])
        blocks = []
        for h in headings:
            parent = h.find_parent(["article", "div", "li", "section"])
            if parent and parent not in blocks:
                blocks.append(parent)
        if len(blocks) >= 3:
            return blocks

        return []

    def extract_item_data(self, item: Tag) -> dict:
        """
        Extract structured fields (title, url, text, price, tags) from an item block.
        """
        data = {}

        # 1. Title and URL
        title_link = None
        for heading_tag in ["h1", "h2", "h3", "h4", "h5"]:
            heading = item.find(heading_tag)
            if heading:
                title_link = heading.find("a")
                if title_link:
                    data["title"] = title_link.get("title") or heading.get_text(strip=True)
                    data["url"] = urljoin(self.base_url, title_link.get("href", ""))
                    break
                data["title"] = heading.get_text(strip=True)
                break

        if "title" not in data:
            any_link = item.find("a")
            if any_link:
                data["title"] = any_link.get("title") or any_link.get_text(strip=True)
                data["url"] = urljoin(self.base_url, any_link.get("href", ""))

        # 2. Detect price if present (£, $, €, ₺)
        price_match = re.search(r"([£$€₺])\s*([0-9]+[.,][0-9]{2})", item.get_text())
        if price_match:
            currency, amount_str = price_match.groups()
            amount = float(amount_str.replace(",", "."))
            data["price"] = amount
            data["currency"] = currency

        # 3. Extract text snippet / description
        paragraphs = item.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and not (price_match and amount_str in text) and len(text) > 5:
                if "description" not in data:
                    data["description"] = text
                    break

        return data

    def extract_all(self, soup: BeautifulSoup) -> list[dict]:
        """Discover items and extract structured records."""
        items = self.find_repeating_items(soup)
        results = []
        for item in items:
            record = self.extract_item_data(item)
            if record and ("title" in record or "url" in record):
                results.append(record)
        return results

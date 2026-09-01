"""Universal data extractor engine for ScrapeAgent."""
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag


class UniversalExtractor:
    """
    Intelligent extractor capable of identifying repeating item patterns
    (products, articles, listings) as well as single-entity structured metadata (JSON-LD, OpenGraph)
    across any website.
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

        # 3. Universal repeating class cluster detector (any container repeating 3+ times with content)
        grid_noise = re.compile(r"^(col-|row|container|clearfix|grid|wrap)", re.I)
        candidate_tags = soup.find_all(["div", "li", "section"])
        class_groups = {}
        for tag in candidate_tags:
            classes = tag.get("class", [])
            valid_classes = [c for c in classes if not grid_noise.match(c)]
            if valid_classes and len(tag.get_text(strip=True)) > 15:
                sig = (tag.name, " ".join(sorted(valid_classes)))
                class_groups.setdefault(sig, []).append(tag)

        candidates = [tags for sig, tags in class_groups.items() if len(tags) >= 3]
        if candidates:
            candidates.sort(key=lambda group: len(group) * min(len(group[0].get_text(strip=True)), 200), reverse=True)
            return candidates[0]

        # 4. Fallback: Repeated links with headings
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

    def extract_single_entity(self, soup: BeautifulSoup) -> list[dict]:
        """
        Extract single-entity structured metadata (JSON-LD, OpenGraph, or meta tags)
        when no repeating catalog cards are found (e.g. dataset pages, articles, single products).
        """
        # 1. Try application/ld+json
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                raw_json = json.loads(script.string.strip())
                items = raw_json if isinstance(raw_json, list) else [raw_json]
                for entry in items:
                    if not isinstance(entry, dict):
                        continue
                    entity = {}
                    entity["title"] = entry.get("name") or entry.get("headline")
                    entity["type"] = entry.get("@type", "Entity")
                    entity["url"] = entry.get("url") or self.base_url

                    # Creator / Author
                    creator = entry.get("creator") or entry.get("author")
                    if isinstance(creator, dict):
                        entity["creator"] = creator.get("name")
                    elif isinstance(creator, list) and creator:
                        entity["creator"] = creator[0].get("name") if isinstance(creator[0], dict) else str(creator[0])
                    elif creator:
                        entity["creator"] = str(creator)

                    # Description
                    desc = entry.get("description", "")
                    if desc:
                        clean_desc = re.sub(r"[#*`]", "", desc).strip()
                        entity["description"] = clean_desc[:200] + "..." if len(clean_desc) > 200 else clean_desc

                    # Keywords
                    keywords = entry.get("keywords")
                    if isinstance(keywords, list):
                        entity["keywords"] = ", ".join(str(k) for k in keywords)
                    elif keywords:
                        entity["keywords"] = str(keywords)

                    if entry.get("license"):
                        lic = entry["license"]
                        entity["license"] = lic.get("name") if isinstance(lic, dict) else str(lic)

                    if entity.get("title"):
                        return [entity]
            except Exception:
                continue

        # 2. Try OpenGraph / Twitter meta tags
        og_data = {}
        for meta in soup.find_all("meta"):
            prop = meta.get("property") or meta.get("name", "")
            content = meta.get("content", "")
            if not prop or not content:
                continue
            if prop in ("og:title", "twitter:title"):
                og_data.setdefault("title", content)
            elif prop in ("og:description", "description", "twitter:description"):
                og_data.setdefault("description", content)
            elif prop in ("og:url",):
                og_data.setdefault("url", content)
            elif prop in ("og:type",):
                og_data.setdefault("type", content)

        if og_data.get("title"):
            og_data.setdefault("url", self.base_url)
            return [og_data]

        # 3. Fallback to HTML <title> tag
        page_title = soup.find("title")
        if page_title and page_title.get_text(strip=True):
            return [{
                "title": page_title.get_text(strip=True),
                "url": self.base_url,
                "type": "WebPage",
            }]

        return []

    def extract_all(self, soup: BeautifulSoup) -> list[dict]:
        """
        Discover items and extract structured records.
        Prioritizes repeating catalog items, then falls back to single-entity metadata.
        """
        items = self.find_repeating_items(soup)
        results = []
        for item in items:
            record = self.extract_item_data(item)
            if record and ("title" in record or "url" in record):
                results.append(record)

        # If no repeating catalog cards found, fallback to single entity metadata
        if not results:
            results = self.extract_single_entity(soup)

        return results

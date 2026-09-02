"""Universal pattern discovery and data extraction engine."""
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag


class UniversalExtractor:
    """Extract repeating list, card, and table records from HTML markup."""

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

    def extract_tables(self, soup: BeautifulSoup) -> list[dict]:
        """
        Extract structured records from HTML <table> elements (e.g. government,
        earthquake, financial, and statistical tables).
        """
        tables = soup.find_all("table")
        candidate_tables = []

        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue

            # 1. Identify headers from <thead> or first <tr>
            headers = []
            header_row = table.find("thead")
            if header_row:
                th_tags = header_row.find_all(["th", "td"])
                headers = [re.sub(r"\s+", " ", th.get_text(strip=True)) for th in th_tags if th.get_text(strip=True)]

            data_rows = rows
            if not headers:
                first_row = rows[0]
                th_tags = first_row.find_all(["th", "td"])
                headers = [re.sub(r"\s+", " ", th.get_text(strip=True)) for th in th_tags if th.get_text(strip=True)]
                data_rows = rows[1:]

            if not headers:
                continue

            # Ensure unique column names
            clean_headers = []
            seen = {}
            for h in headers:
                count = seen.get(h, 0)
                clean_name = f"{h}_{count + 1}" if count > 0 else h
                clean_headers.append(clean_name)
                seen[h] = count + 1

            table_records = []
            for row in data_rows:
                cells = row.find_all("td")
                if not cells or len(cells) < max(2, len(clean_headers) // 2):
                    continue

                record = {}
                for idx, cell in enumerate(cells):
                    if idx < len(clean_headers):
                        val = re.sub(r"\s+", " ", cell.get_text(strip=True))
                        record[clean_headers[idx]] = val

                    # Extract link if present in cell
                    link_tag = cell.find("a")
                    if link_tag and "href" in link_tag.attrs:
                        full_link = urljoin(self.base_url, link_tag["href"])
                        if "url" not in record:
                            record["url"] = full_link

                if record:
                    # Provide a friendly 'title' alias if missing for universal consumers
                    if "title" not in record:
                        preferred_name = record.get("Yer") or record.get("Name") or record.get("Item") or record.get(clean_headers[0])
                        if preferred_name:
                            record["title"] = preferred_name
                    table_records.append(record)

            if len(table_records) >= 3:
                candidate_tables.append(table_records)

        if candidate_tables:
            candidate_tables.sort(key=len, reverse=True)
            return candidate_tables[0]

        return []

    def extract_all(self, soup: BeautifulSoup) -> list[dict]:
        """
        Discover items and extract structured records.
        Prioritizes HTML data tables and repeating catalog cards, then falls back to single-entity metadata.
        """
        # 1. First inspect HTML tables (e.g. AFAD Son Depremler, financial, statistics)
        table_records = self.extract_tables(soup)
        if len(table_records) >= 3:
            return table_records

        # 2. Check for repeating item cards
        items = self.find_repeating_items(soup)
        results = []
        for item in items:
            record = self.extract_item_data(item)
            if record and ("title" in record or "url" in record):
                results.append(record)

        # 3. If no repeating catalog cards found, fallback to single entity metadata
        if not results:
            results = self.extract_single_entity(soup)

        return results

"""HTML temizleme modülü."""
from bs4 import BeautifulSoup, Comment

UNWANTED_TAGS = [
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "iframe",
    "form",
    "button",
]


def clean_html(html_content: str) -> BeautifulSoup:
    """Gereksiz etiketleri ve yorumları HTML içeriğinden temizler."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted scripts, but KEEP type="application/ld+json" (metadata)
    for script in soup.find_all("script"):
        script_type = script.get("type", "").lower()
        if script_type != "application/ld+json":
            script.decompose()

    # Remove other noise tags
    for tag_name in ["style", "noscript", "svg", "canvas", "iframe", "form", "button"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    return soup


def extract_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Locate the core content container (main, article, or body).
    """
    main_container = soup.find("main") or soup.find("div", id="content") or soup.find("body") or soup
    return main_container

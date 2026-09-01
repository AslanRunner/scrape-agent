"""HTML cleaner and DOM optimizer module for ScrapeAgent."""
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
    """
    Parse HTML and strip noise (scripts, styles, tracking tags, comments).

    Args:
        html_content: Raw HTML string.

    Returns:
        Cleaned BeautifulSoup tree.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted noise tags
    for tag in soup.find_all(UNWANTED_TAGS):
        tag.decompose()

    return soup


def extract_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Locate the core content container (main, article, or body).
    """
    main_container = soup.find("main") or soup.find("div", id="content") or soup.find("body") or soup
    return main_container

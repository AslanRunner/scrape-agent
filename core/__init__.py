"""Core modules for ScrapeAgent."""
from .fetcher import fetch_page
from .browser_fetcher import fetch_page_browser
from .cleaner import clean_html, extract_main_content
from .extractor import UniversalExtractor
from .exporter import export_data

__all__ = [
    "fetch_page",
    "fetch_page_browser",
    "clean_html",
    "extract_main_content",
    "UniversalExtractor",
    "export_data",
]

"""Configuration settings for ScrapeAgent."""

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (ScrapeAgent/1.0)"
POLITE_USER_AGENT = "Mozilla/5.0 (compatible; ScrapeAgent/1.0; +https://github.com/AslanRunner/scrape-agent)"

DEFAULT_TIMEOUT = 15
DEFAULT_ENCODING = "utf-8"

# Output directory
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

# Supported export formats
SUPPORTED_FORMATS = ["csv", "json"]

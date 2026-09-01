"""Web istek modülü."""
import requests
from config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT


def fetch_page(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """Hedef sayfayı requests ile çeker ve UTF-8 kodlamasını garanti eder."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    # Ensure UTF-8 or auto-detected encoding so special characters/currencies are not garbled
    if response.encoding is None or response.encoding.lower() in ("iso-8859-1", "ascii"):
        response.encoding = response.apparent_encoding or "utf-8"

    return response

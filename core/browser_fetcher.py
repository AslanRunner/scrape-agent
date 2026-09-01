"""
Headless browser rendering module using Playwright.
Executes client-side JavaScript, handles dynamic Single-Page Applications (SPA),
and retrieves fully rendered DOM markup.
"""
import sys


def fetch_page_browser(url: str, timeout_ms: int = 30000, headless: bool = True) -> str:
    """
    Render a web page using a headless Chromium browser instance.

    Args:
        url: Target web page URL.
        timeout_ms: Maximum navigation timeout in milliseconds.
        headless: Whether to run the browser in headless mode.

    Returns:
        Fully rendered HTML source string.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required for browser-rendered scraping.\n"
            "Install it via:\n"
            "  python -m pip install playwright\n"
            "  playwright install chromium"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        )

        page = context.new_page()

        # Evade basic automation detection
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Give short interval for initial asynchronous hydration/scripts
            page.wait_for_timeout(2000)
            rendered_html = page.content()
        finally:
            context.close()
            browser.close()

    return rendered_html

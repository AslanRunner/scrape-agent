"""Headless browser rendering module using Playwright."""
import sys


def fetch_page_browser(url: str, timeout_ms: int = 30000, headless: bool = True) -> str:
    """Render dynamic JavaScript/SPA pages using Chromium and return HTML source."""
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
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ]

        # Prefer installed Google Chrome for higher trust score, fallback to bundled Chromium
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=headless,
                args=launch_args,
                ignore_default_args=["--enable-automation"],
            )
        except Exception:
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args,
                ignore_default_args=["--enable-automation"],
            )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        )

        page = context.new_page()

        # Stealth evasion scripts
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Give short interval for initial asynchronous hydration/scripts
            page.wait_for_timeout(2000)
            rendered_html = page.content()
        finally:
            context.close()
            browser.close()

    return rendered_html

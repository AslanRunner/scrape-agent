"""ScrapeAgent komut satırı arayüzü."""
import argparse
import os
import re
import subprocess
import sys
from urllib.parse import urlparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.extractor import UniversalExtractor
from core.exporter import export_data
from config import DEFAULT_OUTPUT_DIR

URL_REGEX = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    normalized = normalize_url(url)
    try:
        parsed = urlparse(normalized)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        return bool(URL_REGEX.match(normalized))
    except Exception:
        return False


def derive_default_filename(url: str, ext: str = "csv") -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]", "_", domain)
    path_slug = re.sub(r"[^a-zA-Z0-9]", "_", parsed.path.strip("/"))
    if path_slug:
        slug = f"{slug}_{path_slug}"
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"{slug[:45]}.{ext}"


def check_bot_protection(soup) -> str | None:
    title = soup.find("title")
    title_text = title.get_text().lower() if title else ""
    if any(sig in title_text for sig in ["recaptcha", "checking your browser", "just a moment...", "cloudflare"]):
        return "Cloudflare / reCAPTCHA"
    if any(sig in title_text for sig in ["attention required", "access denied", "security check", "robot or human?"]):
        return "Erişim Engellendi (Bot Koruması)"
    return None


def run_agent(url: str, output_path: str | None = None, use_browser: bool = False) -> None:
    if not is_valid_url(url):
        print(f"Hata: Geçersiz URL -> '{url}'")
        return

    url = normalize_url(url)
    if not output_path:
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, derive_default_filename(url, ext="csv"))

    engine = "Playwright" if use_browser else "HTTP"
    print(f"\nBağlanılıyor: {url} [{engine}]")

    try:
        if use_browser:
            from core.browser_fetcher import fetch_page_browser
            html_text = fetch_page_browser(url)
        else:
            response = fetch_page(url)
            html_text = response.text

        soup = clean_html(html_text)

        block = check_bot_protection(soup)
        if block:
            print(f"Bot engeli tespit edildi: {block}")
            return

        extractor = UniversalExtractor(base_url=url)
        results = extractor.extract_all(soup)

        if not results:
            print("Sayfada yapısal veri bulunamadı.")
            if not use_browser:
                print("İpucu: JavaScript tabanlı siteler için '--browser' seçeneğini deneyebilirsiniz.")
            return

        print(f"{len(results)} kayıt çıkarıldı.\n")

        # İlk 5 kaydı önizleme olarak göster
        print("--- İlk 5 Kayıt ---")
        for i, item in enumerate(results[:5], 1):
            title = item.get("title", "Başlık Yok")
            disp_title = title if len(title) <= 50 else title[:47] + "..."
            price_info = f"{item.get('currency', '')}{item.get('price', '')}" if "price" in item else ""
            print(f"  {i}. {disp_title} {price_info}")

        if len(results) > 5:
            print(f"  ... ve {len(results) - 5} kayıt daha.")

        saved_file = export_data(results, output_path)
        print(f"\nKaydedildi: {saved_file}")

    except Exception as e:
        print(f"Hata: {e}")


def open_output_folder():
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    print(f"\nKlasör açılıyor: {DEFAULT_OUTPUT_DIR}")
    if sys.platform == "win32":
        os.startfile(DEFAULT_OUTPUT_DIR)
    else:
        subprocess.Popen(["xdg-open", DEFAULT_OUTPUT_DIR])


def launch_gui():
    script_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "desktop_gui.py")
    print("\nMasaüstü arayüzü başlatılıyor...")
    subprocess.Popen([sys.executable, script_path])


def interactive_menu():
    while True:
        print("\n==============================")
        print("         ScrapeAgent          ")
        print("==============================")
        print("1. URL Kazı (Hızlı HTTP)")
        print("2. URL Kazı (Playwright Tarayıcı)")
        print("3. Masaüstü Arayüzünü Başlat")
        print("4. Çıktı Klasörünü Aç")
        print("5. Çıkış")

        choice = input("\nSeçiminiz (1-5) [1]: ").strip() or "1"

        if choice in ("1", "2"):
            use_browser = choice == "2"
            while True:
                raw_url = input("\nHedef URL ('iptal' için boş bırakın): ").strip()
                if not raw_url or raw_url.lower() == "iptal":
                    break
                if is_valid_url(raw_url):
                    url = normalize_url(raw_url)
                    auto_name = derive_default_filename(url, ext="csv")
                    out_input = input(f"Dosya adı [Enter: '{auto_name}']: ").strip()
                    output_file = out_input if out_input else auto_name
                    run_agent(url, output_path=output_file, use_browser=use_browser)
                    break
                print(f"Geçersiz URL formatı: '{raw_url}'")

            input("\nMenüye dönmek için Enter'a basın...")

        elif choice == "3":
            launch_gui()
            input("\nMenüye dönmek için Enter'a basın...")

        elif choice == "4":
            open_output_folder()
            input("\nMenüye dönmek için Enter'a basın...")

        elif choice == "5":
            print("\nÇıkış yapıldı.")
            break
        else:
            print("Lütfen 1-5 arasında bir değer seçin.")


def main():
    parser = argparse.ArgumentParser(description="ScrapeAgent - Web Veri Kazıyıcı")
    parser.add_argument("--url", "-u", type=str, help="Kazınacak hedef web adresi")
    parser.add_argument("--output", "-o", type=str, default=None, help="Çıktı dosyası yolu (.csv veya .json)")
    parser.add_argument("--browser", "-b", action="store_true", help="Dinamik JavaScript sayfaları için Playwright kullan")
    parser.add_argument("--gui", "-g", action="store_true", help="Masaüstü grafik arayüzünü başlat")

    args = parser.parse_args()

    if args.gui:
        launch_gui()
    elif args.url:
        run_agent(args.url, output_path=args.output, use_browser=args.browser)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()

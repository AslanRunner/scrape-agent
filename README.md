# ScrapeAgent

Web sitelerinden otomatik olarak yapısal veri (tablolar, kartlar, listeler vb.) çıkaran ve CSV/JSON formatında dışa aktaran masaüstü ve komut satırı aracı.

---

## Özellikler

- **Şablonsuz Veri Çıkarma:** Manuel CSS veya XPath seçicisi girmeden sayfadaki tekrarlayan yapıları (ürünler, haberler, listeler ve tablolar) otomatik tespit eder.
- **İki Farklı Çalışma Motoru:**
  - **Hızlı HTTP:** Standart HTML sayfaları için hafif ve hızlı istek motoru.
  - **Playwright (Chromium):** JavaScript ile sonradan yüklenen dinamik sayfalar (SPA) için tam tarayıcı render desteği.
- **Karanlık ve Aydınlık Tema:** Gözü yormayan modern sıcak kehribar (Warm Amber) renk paleti ve tek tıkla mod geçişi.
- **Canlı Tablo ve Arama:** Çekilen verileri arayüzdeki tabloda görüntüleme ve anlık arama/filtreleme.
- **Dışa Aktarma:** Verileri tek tıkla `.csv` veya `.json` olarak kaydetme.
- **CLI & GUI:** İster grafik arayüzden, ister terminalden tek komutla kullanım.

---

## Kurulum

1. Depoyu klonlayın ve klasöre girin:
```bash
git clone https://github.com/AslanRunner/scrape-agent.git
cd scrape-agent
```

2. Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

3. *(Opsiyonel - Dinamik JavaScript sitelerini tarayıcı ile kazımak için)*:
```bash
playwright install chromium
```

---

## Kullanım

### 1. Masaüstü Grafik Arayüzü (GUI)
Uygulamayı başlatmak için `ScrapeAgent.bat` dosyasına çift tıklayabilir veya terminalden çalıştırabilirsiniz:

```bash
python desktop_gui.py
```

### 2. Komut Satırı (CLI)

**Etkileşimli Menü:**
```bash
python agent.py
```

**Doğrudan Komutla Kazıma:**
```bash
# Standart HTTP ile CSV olarak kaydetme
python agent.py --url "https://ornek-site.com" --output "veriler.csv"

# Dinamik JavaScript siteleri için tarayıcı motoruyla kazıma
python agent.py --url "https://ornek-site.com" --browser --output "veriler.json"
```

---

## Proje Yapısı

```text
scrape-agent/
├── desktop_gui.py      # CustomTkinter tabanlı masaüstü grafik arayüzü
├── agent.py            # Komut satırı arayüzü ve terminal menüsü
├── config.py           # Zaman aşımı ve çıktı klasörü ayarları
├── ScrapeAgent.bat     # Windows başlatıcı
├── run.bat             # Terminal başlatıcı
├── requirements.txt    # Python bağımlılıkları
├── assets/             # İkon ve görsel dosyaları
├── output/             # Çıkarılan verilerin kaydedildiği klasör
└── core/               # Kazıma motoru çekirdek modülleri
    ├── fetcher.py      # HTTP istek modülü (requests)
    ├── browser_fetcher.py # Headless Chromium modülü (Playwright)
    ├── cleaner.py      # HTML temizleme ve ayrıştırma
    ├── extractor.py    # Otomatik yapısal veri çıkarma motoru
    └── exporter.py     # CSV ve JSON dönüştürücü
```

---

## Lisans

Bu proje [MIT](LICENSE) lisansı ile lisanslanmıştır.

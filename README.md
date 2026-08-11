# 🚀 ProCheck v2.0 - Advanced Proxy Scraper & Checker

İnternetteki 25+ güncel public proxy listelerinden **HTTP, HTTPS, SOCKS4, SOCKS5** proxylerini otomatik çeken, yüksek hızlı (multi-threaded async) test edip doğrulayan gelişmiş Proxy Scraper & Checker uygulaması.

---

## ✨ Özellikler

- 🌐 **Otomatik Scrape**: 25+ farklı güvenilir GitHub ve API kaynağından (TheSpeedX, Monosans, ProxyScrape, Geonode vb.) binlerce proxyle 1 tıkla çekme.
- ⚡ **Yüksek Hızlı Async Checker**: Python `asyncio` ve `aiohttp` / `aiohttp-socks` ile aynı anda 150-500 thread ile ultra hızlı test.
- 🔒 **Protokol & Anonimlik Tespiti**: HTTP, HTTPS, SOCKS4, SOCKS5 protokolu ve Transparent, Anonymous, Elite/High anonimlik seviyesi testi.
- ⏱️ **Gecikme (Ping/Latency) Hesabı**: Her proxy için milisaniye (ms) cinsinden yanıt süresi.
- 🎨 **Lüks Web Arayüzü (Dashboard)**: Neon temalı, canlı istatistik kartları, filtreleme (Protokol, Durum, Ping, Arama), gerçek zamanlı WebSocket aktarımı.
- 💾 **Çoklu Format Dışa Aktarma**: TXT (IP:Port), JSON, CSV formatında indirme veya tek tıkla panoya kopyalama.
- 🖥️ **CLI Desteği**: Komut satırından hızlı kullanım imkanı.

---

## 🛠️ Kurulum & Çalıştırma

### Yöntem 1: Web Arayüzü (Önerilen)

Windows kullanıyorsanız tek tıkla başlatmak için:
`run.bat` dosyasına çift tıklayın!

Veya manuel olarak:
```bash
# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Web sunucusunu başlatın
python server.py
```
Tarayıcınızda `http://127.0.0.1:8000` adresine gidin.

---

### Yöntem 2: Komut Satırı (CLI)

```bash
# Hem kazıma (scrape) hem test (check) yapmak için:
python cli.py --scrape --check

# Özel proxy dosyanızı test etmek için:
python cli.py --input my_proxies.txt --output working.txt

# Thread sayısı ve zaman aşımı (timeout) ayarlayarak çalıştırmak için:
python cli.py --scrape --check --concurrency 250 --timeout 3.5
```

---

## 📂 Dosya Yapısı

```
iplog/
├── backend/
│   ├── scraper.py          # 25+ kaynaktan proxy çekme modülü
│   ├── checker.py          # Async proxy doğrulama ve test motoru
│   └── manager.py          # Durum yönetimi ve dosya kaydetme
├── static/
│   ├── index.html          # Web UI HTML
│   ├── style.css           # Glassmorphism & Dark Mode stilleri
│   └── app.js              # Canlı WebSocket & Filtreleme logic
├── data/                   # Test sonuçlarının kaydedildiği klasör
│   ├── proxies_alive.txt   # Çalışan tüm proxyler (IP:Port)
│   ├── proxies_http.txt    # HTTP/S çalışanlar
│   ├── proxies_socks4.txt  # SOCKS4 çalışanlar
│   ├── proxies_socks5.txt  # SOCKS5 çalışanlar
│   └── results.json        # Tüm detaylı sonuçlar
├── server.py               # FastAPI backend web sunucusu
├── cli.py                  # CLI çalıştırıcısı
├── run.bat                 # Windows kolay başlatıcı
└── requirements.txt        # Python kütüphaneleri
```

# Firebase Web & Cloud Functions Deployment Guide

Bu rehber, **Discord Coin + CPX Research Ödül Sistemi** uygulamasını **Firebase Hosting** (Frontend) ve **Firebase Cloud Functions 2. Nesil (Python)** (Backend API) üzerine canlıya alma adımlarını içerir.

---

## 🏗️ 1. Hazırlık ve Yapılandırma

Projeye Firebase konfigürasyon dosyaları eklenmiştir:

- `firebase.json`: Hosting yönlendirmelerini (rewrites) ve Cloud Functions Python 3.11 çalışma zamanını belirler.
- `functions/main.py`: FastAPI uygulamasını Firebase Cloud Functions ortamına bağlayan ASGI Mangum adapte edicisidir.
- `functions/requirements.txt`: Cloud Functions sunucusunda çalışacak Python paketleridir.

---

## ⚡ 2. Adım Adım Firebase Deploy İşlemi

### Adım 1: Firebase CLI Girişi Yapın
Terminalinizde aşağıdaki komutu çalıştırarak Google/Firebase hesabınızla oturum açın:

```bash
npx firebase-tools login
```

### Adım 2: Firebase Projenizi Seçin (Init)
Eğer henüz bir Firebase projesi oluşturmadıysanız [Firebase Console](https://console.firebase.google.com/) üzerinden yeni bir proje oluşturun.

Ardından projeyi bağlayın:
```bash
npx firebase-tools use --add
```
*(Listeden oluşturduğunuz Firebase projesini seçin ve takma ad olarak `default` verin).*

### Adım 3: Ortam Değişkenlerini (Secrets) Tanımlayın
Canlı ortamda CPX Secure Hash ve Discord Secret değerlerinizi tanımlayın:

```bash
npx firebase-tools functions:secrets:set CPX_APP_SECURE_HASH
npx firebase-tools functions:secrets:set DISCORD_BOT_TOKEN
npx firebase-tools functions:secrets:set DISCORD_CLIENT_ID
npx firebase-tools functions:secrets:set DISCORD_CLIENT_SECRET
```

*(Veya `DATABASE_URL` için canlı PostgreSQL bağlantı adresinizi Supabase / Neon.tech / Cloud SQL adresi olarak girin).*

### Adım 4: Tek Komutla Canlıya Alın (Deploy)

```bash
npx firebase-tools deploy
```

Deploy tamamlandığında Firebase size canlı URL adresinizi verecektir:
`https://<proje-id>.web.app`

---

## 🌐 3. CPX Research Panel Güncellemesi

Firebase'e yüklendikten sonra CPX Research yayıncı panelinizdeki (App ID: `35266`) **Postback URL** adresini güncelleyin:

```text
https://<proje-id>.web.app/api/cpx/postback
```

---

## 🤖 4. Discord Botunun Canlı Ortamda Çalışması

> **Önemli Not:** Firebase Cloud Functions sunucusuz (serverless) yapıda olduğu için istek gelmediğinde kapanır (scale to zero). Discord botunun 7/24 kesintisiz açık kalabilmesi için `bot/bot.py` dosyasını ücretsiz/düşük maliyetli bir container ortamında (Railway, Render, Fly.io veya VPS) çalıştırabilirsiniz. Bot ve Web uygulaması aynı PostgreSQL veritabanını paylaşarak senkronize çalışır.

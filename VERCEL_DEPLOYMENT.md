# Vercel Deployment Guide

Bu proje **Vercel** üzerinde hem Frontend hem de Python FastAPI Backend Serverless Function olarak çalışacak şekilde yapılandırılmıştır.

---

## 🛠️ Yapılan Yapılandırmalar

- `api/index.py`: FastAPI backend uygulamasını Vercel Python Serverless çalışma zamanına bağlar.
- `vercel.json`: `/api/**` isteklerini Python fonksiyonuna, `/tasks` ve `/admin-panel` yollarını ilgili HTML sayfalarına yönlendirir.

---

## ⚡ Vercel'e Deploy Etme Adımları

Terminalinizde şu komutu çalıştırın:

```cmd
npx vercel --prod
```

### İlk Kurulum Soruları (Sırasıyla):
1. **Set up and deploy?** `Y` (Enter)
2. **Which scope?** *(Hesabınızı seçin, Enter)*
3. **Link to existing project?** `N` (Enter)
4. **What's your project's name?** `surveytr` (veya istediğiniz isim)
5. **In which directory is your code located?** `./` (Enter)
6. **Want to modify these settings?** `N` (Enter)

---

## 🌐 Deploy Bittiğinde

Vercel size canlı URL adresinizi verecektir:
`https://surveytr.vercel.app` (veya belirlediğiniz isim).

### CPX Postback Adresiniz:
```text
https://surveytr.vercel.app/api/cpx/postback
```

# Wallify CDN Yönetim Paneli

Bu proje, Wallify CDN servisini yönetmek için Django tabanlı bir yönetim panelidir. Bu panel, CDN servisinin API'sini kullanarak dosya ve koleksiyon yönetimini sağlar.

## Özellikler

- Koleksiyon (klasör) yönetimi: oluşturma, düzenleme, silme
- Dosya yönetimi: yükleme, düzenleme, silme, taşıma
- Toplu dosya yükleme
- Filtreleme ve arama özellikleri
- CDN ile senkronizasyon
- Responsive tasarım

## Mimari

Bu yönetim paneli, veritabanı bağlantısı olmadan çalışır. Tüm veri işlemleri doğrudan CDN API'si ve dosya sistemi üzerinden gerçekleştirilir:

- **CDN API Entegrasyonu**: Tüm veri işlemleri wallify_cdn.py API'si üzerinden yapılır
- **Dosya Sistemi**: Dosya ve koleksiyon bilgileri doğrudan CDN klasöründen okunur
- **Django**: Sadece frontend ve kullanıcı arayüzü için kullanılır, veritabanı işlemleri yapmaz

## Kurulum

### Gereksinimler

- Python 3.8+
- Django 4.2+
- Wallify CDN Servisi

### Adımlar

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Django uygulamasını başlatın:
```bash
cd wallify_admin
python manage.py runserver
```

3. Tarayıcınızda `http://localhost:8000` adresine gidin

## CDN Servis Entegrasyonu

Bu yönetim paneli, Wallify CDN servisi ile entegre çalışır. CDN servisinin çalışır durumda olduğundan emin olun:

```bash
# CDN servisini başlatmak için
cd ..
python wallify_cdn.py
```

CDN servisi varsayılan olarak `http://localhost:9545` adresinde çalışır. Bu adresi değiştirmek için `config/settings.py` dosyasındaki `CDN_API_URL` değişkenini güncelleyin.

## Dizin Yapısı

```
wallify_admin/
├── config/             # Proje ayarları
├── dashboard/          # Ana uygulama
│   ├── models.py       # Veri modelleri (sadece frontend gösterimi için)
│   ├── views.py        # Görünüm fonksiyonları
│   ├── utils.py        # CDN API ile iletişim için yardımcı fonksiyonlar
│   ├── forms.py        # Form sınıfları
│   └── urls.py         # URL yapılandırması
├── templates/          # HTML şablonları
│   └── dashboard/      # Dashboard şablonları
└── static/             # Statik dosyalar
    └── dashboard/      # Dashboard CSS ve JS dosyaları
```

## Veritabanı Kullanımı

Bu uygulama, veritabanını sadece Django'nun dahili işlemleri (oturum yönetimi, kullanıcı kimlik doğrulama vb.) için kullanır. Tüm CDN dosya ve koleksiyon işlemleri doğrudan API ve dosya sistemi üzerinden gerçekleştirilir.

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 
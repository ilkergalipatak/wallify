# Wallify

Wallify, duvar kağıdı ve görsel koleksiyonlarını yönetmek için geliştirilmiş bir CDN (İçerik Dağıtım Ağı) uygulamasıdır. Flask tabanlı bir API ve Django tabanlı bir yönetim paneli içerir.

## Özellikler

- **Görsel Yönetimi**: Görselleri kolayca yükleyin, düzenleyin ve silin
- **Koleksiyon Sistemi**: Görselleri koleksiyonlara ayırarak düzenleyin
- **API Erişimi**: JWT tabanlı kimlik doğrulama ile güvenli API erişimi
- **Görsel Yeniden Boyutlandırma**: Görselleri isteğe bağlı olarak yeniden boyutlandırma
- **Yönetim Paneli**: Kullanıcı dostu Django tabanlı yönetim paneli

## Sistem Gereksinimleri

- Python 3.10 veya üzeri
- PostgreSQL 14 veya üzeri
- Docker ve Docker Compose (isteğe bağlı)

## Kurulum

### Çevre Değişkenleri

Projeyi çalıştırmadan önce, `env.example` dosyasını `.env` olarak kopyalayın ve gerekli değişkenleri ayarlayın:

```bash
cp env.example .env
```

Ardından `.env` dosyasını düzenleyerek aşağıdaki değişkenleri ayarlayın:
- `DB_USER`: PostgreSQL kullanıcı adı
- `DB_PASSWORD`: PostgreSQL şifresi
- `DB_NAME`: PostgreSQL veritabanı adı
- `DB_HOST`: PostgreSQL sunucu adresi
- `JWT_SECRET`: JWT token'ları için güvenli bir anahtar (rastgele bir string)

### Docker ile Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/kullanici_adiniz/wallify.git
cd wallify
```

2. `.env` dosyasını oluşturun (yukarıdaki adımları takip edin)

3. Docker Compose ile uygulamayı başlatın:
```bash
docker-compose up -d
```

Detaylı bilgi için `README_DOCKER.md` dosyasını inceleyebilirsiniz.

### Manuel Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/kullanici_adiniz/wallify.git
cd wallify
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. `.env` dosyasını oluşturun (yukarıdaki adımları takip edin)

4. PostgreSQL veritabanını oluşturun:
```bash
createdb wallify
```

5. Flask API'yi başlatın:
```bash
python wallify_cdn.py
```

6. Django yönetim panelini başlatın:
```bash
cd wallify_admin
python manage.py migrate
python manage.py runserver
```

## Kullanım

- **API Erişimi**: `http://localhost:9545`
- **Yönetim Paneli**: `http://localhost:8000`

## Katkıda Bulunma

1. Bu depoyu forklayın
2. Yeni bir dal oluşturun (`git checkout -b ozellik/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: Açıklama'`)
4. Dalınızı push edin (`git push origin ozellik/yeni-ozellik`)
5. Bir Pull Request oluşturun

## Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. 
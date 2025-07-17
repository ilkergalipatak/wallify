# Wallify Docker Kurulumu

Bu belge, Wallify uygulamasının Docker kullanarak nasıl çalıştırılacağını açıklar.

## Gereksinimler

- Docker
- Docker Compose

## Kurulum

1. Projeyi klonlayın veya indirin:

```bash
git clone <repo-url>
cd wallify
```

2. Docker ortamı için gerekli ayarları yapın (isteğe bağlı):

`docker.env` dosyasını düzenleyerek veritabanı şifresi, JWT anahtarı gibi hassas bilgileri değiştirebilirsiniz.

3. Docker Compose ile uygulamayı başlatın:

```bash
docker-compose up -d
```

Bu komut, üç servisi başlatacaktır:
- PostgreSQL veritabanı (`db`)
- Flask API (`flask`) - CDN servisi
- Django Admin Paneli (`django`)

4. Servislerin durumunu kontrol edin:

```bash
docker-compose ps
```

## Erişim

- Django Admin Paneli: http://localhost:8000
- Flask API: http://localhost:9545

## Veritabanı Yönetimi

Veritabanı verilerini kalıcı olarak saklamak için Docker volume kullanılmaktadır. Veritabanı verileri `postgres_data` adlı volume'da saklanır.

## Dosya Paylaşımı

CDN klasörü (`./cdn`), her iki servis ile de paylaşılır, böylece yüklenen dosyalar hem Flask API hem de Django Admin Paneli tarafından erişilebilir.

## Logları Görüntüleme

Herhangi bir servisin loglarını görüntülemek için:

```bash
docker-compose logs -f [servis-adı]
```

Örneğin:
```bash
docker-compose logs -f flask
```

## Servisleri Durdurma

Servisleri durdurmak için:

```bash
docker-compose down
```

Veritabanı verilerini de silmek isterseniz:

```bash
docker-compose down -v
```

## Sorun Giderme

1. **Flask API'ye erişilemiyor**:
   - Flask API'nin çalışıp çalışmadığını kontrol edin: `docker-compose logs flask`
   - PostgreSQL'in çalışıp çalışmadığını kontrol edin: `docker-compose logs db`

2. **Django Admin Paneli'ne erişilemiyor**:
   - Django'nun çalışıp çalışmadığını kontrol edin: `docker-compose logs django`
   - Flask API'nin çalışıp çalışmadığını kontrol edin: `docker-compose logs flask`

3. **Dosya yükleme sorunları**:
   - CDN klasörünün izinlerini kontrol edin
   - Flask API loglarını kontrol edin: `docker-compose logs flask` 
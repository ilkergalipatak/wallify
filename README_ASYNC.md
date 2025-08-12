# Wallify Asenkron Sistem

Bu dokümantasyon, Wallify CDN sisteminin asenkron yapısını açıklar.

## 🚀 Asenkron Sistem Özellikleri

### Yeni Eklenen Servisler

1. **Redis** - Mesaj kuyruğu ve cache için
2. **Celery Worker** - Asenkron görevleri işlemek için
3. **Celery Beat** - Zamanlanmış görevler için
4. **Flower** - Celery monitoring için

### Asenkron Görevler

#### 1. Resim İşleme (`process_image_async`)
- Resim dosyalarını asenkron olarak işler
- Veritabanına kaydeder
- Koleksiyon istatistiklerini günceller

#### 2. Toplu Resim İşleme (`bulk_process_images`)
- Birden fazla resmi paralel olarak işler
- İlerleme durumunu takip eder

#### 3. Thumbnail Oluşturma (`generate_thumbnails`)
- Farklı boyutlarda thumbnail'lar oluşturur (150px, 300px, 600px)
- Aspect ratio'yu korur

#### 4. Orphaned Dosya Temizliği (`cleanup_orphaned_files`)
- Veritabanında olmayan dosyaları temizler
- Her gün gece yarısı çalışır

#### 5. Koleksiyon İstatistikleri Güncelleme (`update_collection_stats`)
- Koleksiyon istatistiklerini günceller
- Her saat başı çalışır

#### 6. Resim Optimizasyonu (`optimize_images`)
- Resimleri optimize eder
- Her gün sabah 6'da çalışır

## 🏗️ Sistem Mimarisi

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │   Django    │    │   Flask     │
│             │    │   Admin     │    │   API       │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │   Redis     │
                    │   Queue     │
                    └─────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Celery    │    │   Celery    │    │   Flower    │
│   Worker    │    │   Beat      │    │   Monitor   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │ Database    │
                    └─────────────┘
```

## 🐳 Docker ile Çalıştırma

### 1. Sistemi Başlatma

```bash
# Tüm servisleri başlat
docker-compose up -d

# Logları izle
docker-compose logs -f
```

### 2. Servis Durumları

```bash
# Servis durumlarını kontrol et
docker-compose ps

# Belirli servisin loglarını izle
docker-compose logs -f flask
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### 3. Test Çalıştırma

```bash
# Asenkron sistem testlerini çalıştır
docker-compose run --rm test

# Manuel test
docker-compose exec flask python test_async_system.py
```

## 📊 Monitoring

### Flower Dashboard
- URL: http://localhost:5555
- Celery görevlerini izleme
- Worker durumları
- Görev geçmişi

### API Endpoint'leri

#### Görev Durumu Kontrolü
```bash
GET /task/status/<task_id>
```

#### Aktif Görevleri Listele
```bash
GET /tasks/active
```

#### Görev İptal Etme
```bash
POST /task/cancel/<task_id>
```

## 🔧 API Kullanımı

### Asenkron Dosya Yükleme

```bash
# Tek dosya asenkron yükleme
curl -X POST http://localhost:7545/file_upload \
  -H "Authorization: YOUR_TOKEN" \
  -F "file=@image.jpg" \
  -F "collection=my_collection" \
  -F "async=true"
```

### Toplu Asenkron Yükleme

```bash
# Çoklu dosya asenkron yükleme
curl -X POST http://localhost:7545/bulk_upload \
  -H "Authorization: YOUR_TOKEN" \
  -F "files[]=@image1.jpg" \
  -F "files[]=@image2.jpg" \
  -F "collection=my_collection" \
  -F "async=true"
```

### Görev Durumu Kontrolü

```bash
# Görev durumunu kontrol et
curl http://localhost:7545/task/status/TASK_ID
```

## ⏰ Zamanlanmış Görevler

### Otomatik Çalışan Görevler

1. **Her gün gece yarısı (00:00)**
   - Orphaned dosya temizliği

2. **Her saat başı (XX:00)**
   - Koleksiyon istatistikleri güncelleme

3. **Her gün sabah 6'da (06:00)**
   - Resim optimizasyonu

### Manuel Görev Tetikleme

```bash
# Manuel olarak görev tetikleme (Django shell)
docker-compose exec django python manage.py shell

# Örnek:
from tasks import cleanup_orphaned_files
result = cleanup_orphaned_files.delay()
print(f"Task ID: {result.id}")
```

## 🔍 Troubleshooting

### Redis Bağlantı Sorunu

```bash
# Redis durumunu kontrol et
docker-compose exec redis redis-cli ping

# Redis loglarını izle
docker-compose logs -f redis
```

### Celery Worker Sorunu

```bash
# Worker durumunu kontrol et
docker-compose exec celery_worker celery -A tasks inspect active

# Worker'ı yeniden başlat
docker-compose restart celery_worker
```

### Görev Durumu Kontrolü

```bash
# Tüm aktif görevleri listele
curl http://localhost:7545/tasks/active

# Belirli görev durumunu kontrol et
curl http://localhost:7545/task/status/TASK_ID
```

## 📈 Performans Optimizasyonu

### Celery Worker Ayarları

```python
# tasks.py içinde
CELERY_WORKER_CONCURRENCY = 4  # Eşzamanlı worker sayısı
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 dakika
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 dakika
```

### Redis Ayarları

```yaml
# docker-compose.yml içinde
redis:
  image: redis:7-alpine
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## 🔒 Güvenlik

### Token Kontrolü
- Tüm asenkron görevler admin token kontrolü yapar
- Görev durumu kontrolü için token gerekli

### Dosya Güvenliği
- Path traversal saldırılarına karşı koruma
- Dosya tipi kontrolü
- Boyut sınırlaması

## 📝 Log Yapısı

### Celery Logları
```bash
# Worker logları
docker-compose logs -f celery_worker

# Beat logları
docker-compose logs -f celery_beat
```

### Flask API Logları
```bash
# API logları
docker-compose logs -f flask
```

## 🚀 Production Deployment

### Environment Variables

```bash
# .env.docker dosyasına ekle
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
REDIS_HOST=redis
DB_HOST=db
DOCKER_ENVIRONMENT=true
```

### Scaling

```bash
# Worker sayısını artır
docker-compose up -d --scale celery_worker=3

# Redis cluster (production için)
# Redis Sentinel veya Redis Cluster kullanın
```

## 📚 Ek Kaynaklar

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Flower Documentation](https://flower.readthedocs.io/)
- [Django Celery Beat](https://django-celery-beat.readthedocs.io/)

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 
#!/bin/bash

# Wallify Asenkron Sistem Başlatma Script'i

set -e

echo "🚀 Wallify Asenkron Sistem Başlatılıyor..."
echo "📅 Başlatma zamanı: $(date)"
echo "=" * 60

# Docker Compose dosyasının varlığını kontrol et
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml dosyası bulunamadı!"
    exit 1
fi

# Mevcut servisleri durdur (varsa)
echo "🛑 Mevcut servisler durduruluyor..."
docker compose down --remove-orphans

# Docker imajlarını yeniden oluştur
echo "🔨 Docker imajları yeniden oluşturuluyor..."
docker compose build --no-cache

# Tüm servisleri başlat
echo "🚀 Servisler başlatılıyor..."
docker compose up -d

# Servislerin başlamasını bekle
echo "⏳ Servislerin başlaması bekleniyor..."
sleep 30

# Servis durumlarını kontrol et
echo "🔍 Servis durumları kontrol ediliyor..."
docker compose ps

# Health check'leri kontrol et
echo "🏥 Health check'ler kontrol ediliyor..."

# PostgreSQL kontrolü
echo "   📊 PostgreSQL kontrol ediliyor..."
if docker compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo "   ✅ PostgreSQL hazır"
else
    echo "   ❌ PostgreSQL hazır değil"
fi

# Redis kontrolü
echo "   🔴 Redis kontrol ediliyor..."
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis hazır"
else
    echo "   ❌ Redis hazır değil"
fi

# Flask API kontrolü
echo "   🐍 Flask API kontrol ediliyor..."
if curl -s http://localhost:7545 > /dev/null 2>&1; then
    echo "   ✅ Flask API hazır"
else
    echo "   ❌ Flask API hazır değil"
fi

# Django Admin kontrolü
echo "   🎯 Django Admin kontrol ediliyor..."
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "   ✅ Django Admin hazır"
else
    echo "   ❌ Django Admin hazır değil"
fi

# Flower kontrolü
echo "   🌸 Flower kontrol ediliyor..."
if curl -s http://localhost:5555 > /dev/null 2>&1; then
    echo "   ✅ Flower hazır"
else
    echo "   ❌ Flower hazır değil"
fi

echo ""
echo "🎉 Sistem başlatma tamamlandı!"
echo ""
echo "📊 Servis URL'leri:"
echo "   🌐 Flask API: http://localhost:7545"
echo "   🎯 Django Admin: http://localhost:8000"
echo "   🌸 Flower Monitor: http://localhost:5555"
echo "   📊 PostgreSQL: localhost:5432"
echo "   🔴 Redis: localhost:6379"
echo ""
echo "🔍 Logları izlemek için:"
echo "   docker compose logs -f"
echo ""
echo "🧪 Test çalıştırmak için:"
echo "   docker compose run --rm test"
echo ""
echo "🛑 Sistemi durdurmak için:"
echo "   docker compose down"
echo ""
echo "=" * 60
echo "✅ Wallify Asenkron Sistem başarıyla başlatıldı!" 
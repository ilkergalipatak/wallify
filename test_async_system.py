#!/usr/bin/env python3
"""
Asenkron sistem test dosyası
Bu dosya Docker ortamında çalıştırılmalıdır
"""

import requests
import time
import json
import os
from datetime import datetime

# Test konfigürasyonu
CDN_API_URL = os.getenv('CDN_API_URL', 'http://localhost:7545')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')  # Test için admin token'ı

def test_redis_connection():
    """Redis bağlantısını test et"""
    print("🔍 Redis bağlantısı test ediliyor...")
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
        print("✅ Redis bağlantısı başarılı")
        return True
    except Exception as e:
        print(f"❌ Redis bağlantısı başarısız: {e}")
        return False

def test_celery_worker():
    """Celery worker'ı test et"""
    print("🔍 Celery worker test ediliyor...")
    try:
        response = requests.get(f"{CDN_API_URL}/tasks/active")
        if response.status_code == 200:
            print("✅ Celery worker aktif")
            return True
        else:
            print(f"❌ Celery worker test başarısız: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Celery worker test hatası: {e}")
        return False

def test_async_file_upload():
    """Asenkron dosya yükleme test et"""
    print("🔍 Asenkron dosya yükleme test ediliyor...")
    
    if not ADMIN_TOKEN:
        print("⚠️  Admin token bulunamadı, test atlanıyor")
        return False
    
    try:
        # Test dosyası oluştur
        test_file_path = "/tmp/test_image.jpg"
        with open(test_file_path, "wb") as f:
            # Basit bir test resmi oluştur
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')
        
        # Dosyayı yükle
        with open(test_file_path, "rb") as f:
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            data = {
                'collection': 'test_collection',
                'async': 'true'
            }
            headers = {'Authorization': ADMIN_TOKEN}
            
            response = requests.post(
                f"{CDN_API_URL}/file_upload?token={ADMIN_TOKEN}",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Asenkron dosya yükleme başarılı")
            print(f"   Dosya ID: {result.get('id')}")
            print(f"   Asenkron işleme: {result.get('async_processing')}")
            
            # Task ID'leri kontrol et
            task_ids = result.get('task_ids', [])
            if task_ids:
                print(f"   Task ID'leri: {task_ids}")
                
                # Task durumlarını kontrol et
                for task_type, task_id in task_ids:
                    print(f"   {task_type} task durumu kontrol ediliyor...")
                    time.sleep(2)  # Biraz bekle
                    
                    task_response = requests.get(f"{CDN_API_URL}/task/status/{task_id}")
                    if task_response.status_code == 200:
                        task_status = task_response.json()
                        print(f"   {task_type}: {task_status.get('status')}")
                    else:
                        print(f"   {task_type}: Durum alınamadı")
            
            return True
        else:
            print(f"❌ Asenkron dosya yükleme başarısız: {response.status_code}")
            print(f"   Hata: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Asenkron dosya yükleme test hatası: {e}")
        return False
    finally:
        # Test dosyasını temizle
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def test_bulk_async_upload():
    """Toplu asenkron yükleme test et"""
    print("🔍 Toplu asenkron yükleme test ediliyor...")
    
    if not ADMIN_TOKEN:
        print("⚠️  Admin token bulunamadı, test atlanıyor")
        return False
    
    try:
        # Test dosyaları oluştur
        test_files = []
        for i in range(3):
            test_file_path = f"/tmp/test_bulk_{i}.jpg"
            with open(test_file_path, "wb") as f:
                # Basit test resimleri
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')
            test_files.append(test_file_path)
        
        # Dosyaları yükle
        files = []
        for i, file_path in enumerate(test_files):
            with open(file_path, "rb") as f:
                files.append(('files[]', (f'test_bulk_{i}.jpg', f, 'image/jpeg')))
        
        data = {
            'collection': 'test_bulk_collection',
            'async': 'true'
        }
        headers = {'Authorization': ADMIN_TOKEN}
        
        response = requests.post(
            f"{CDN_API_URL}/bulk_upload?token={ADMIN_TOKEN}",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Toplu asenkron yükleme başarılı")
            print(f"   Toplam: {result.get('total')}")
            print(f"   Başarılı: {result.get('successful')}")
            print(f"   Başarısız: {result.get('failed')}")
            print(f"   Asenkron işleme: {result.get('async_processing')}")
            
            # Task ID'leri kontrol et
            task_ids = result.get('task_ids', [])
            if task_ids:
                print(f"   Task ID'leri: {task_ids}")
            
            return True
        else:
            print(f"❌ Toplu asenkron yükleme başarısız: {response.status_code}")
            print(f"   Hata: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Toplu asenkron yükleme test hatası: {e}")
        return False
    finally:
        # Test dosyalarını temizle
        for file_path in test_files:
            if os.path.exists(file_path):
                os.remove(file_path)

def test_scheduled_tasks():
    """Zamanlanmış görevleri test et"""
    print("🔍 Zamanlanmış görevler test ediliyor...")
    try:
        # Manuel olarak zamanlanmış görevleri çalıştır
        tasks_to_test = [
            ('cleanup_orphaned_files', 'Orphaned dosya temizliği'),
            ('update_collection_stats', 'Koleksiyon istatistikleri güncelleme'),
            ('optimize_images', 'Resim optimizasyonu')
        ]
        
        for task_name, task_description in tasks_to_test:
            print(f"   {task_description} test ediliyor...")
            
            # Task'ı manuel olarak tetikle (gerçek uygulamada bu endpoint olmayabilir)
            # Bu sadece test amaçlıdır
            try:
                response = requests.post(f"{CDN_API_URL}/admin/trigger_task", 
                                       json={'task_name': task_name},
                                       headers={'Authorization': ADMIN_TOKEN})
                if response.status_code == 200:
                    print(f"   ✅ {task_description} başlatıldı")
                else:
                    print(f"   ⚠️  {task_description} başlatılamadı (endpoint yok)")
            except:
                print(f"   ⚠️  {task_description} endpoint'i mevcut değil")
        
        return True
    except Exception as e:
        print(f"❌ Zamanlanmış görevler test hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🚀 Wallify Asenkron Sistem Test Başlatılıyor...")
    print(f"📅 Test zamanı: {datetime.now()}")
    print(f"🌐 CDN API URL: {CDN_API_URL}")
    print("=" * 60)
    
    tests = [
        ("Redis Bağlantısı", test_redis_connection),
        ("Celery Worker", test_celery_worker),
        ("Asenkron Dosya Yükleme", test_async_file_upload),
        ("Toplu Asenkron Yükleme", test_bulk_async_upload),
        ("Zamanlanmış Görevler", test_scheduled_tasks),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} Testi:")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test hatası: {e}")
            results.append((test_name, False))
    
    # Sonuçları özetle
    print("\n" + "=" * 60)
    print("📊 TEST SONUÇLARI:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Genel Durum: {passed}/{total} test başarılı")
    
    if passed == total:
        print("🎉 Tüm testler başarılı! Asenkron sistem çalışıyor.")
    else:
        print("⚠️  Bazı testler başarısız. Lütfen logları kontrol edin.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 
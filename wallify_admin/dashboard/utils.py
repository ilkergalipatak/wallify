import os
import shutil
import requests
from django.conf import settings
import logging
from pathlib import Path
import time
from functools import lru_cache
import re

logger = logging.getLogger(__name__)

# Önbellek süresi (saniye)
CACHE_TIMEOUT = 60

# Önbellek için basit bir sözlük
_cache = {}

def cache_result(timeout=CACHE_TIMEOUT):
    """Fonksiyon sonuçlarını önbelleğe almak için decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Önbellek anahtarı oluştur
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Önbellekte varsa ve süresi dolmamışsa, önbellekten döndür
            if cache_key in _cache:
                result, timestamp = _cache[cache_key]
                if time.time() - timestamp < timeout:
                    return result
            
            # Fonksiyonu çağır ve sonucu önbelleğe al
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time())
            return result
        return wrapper
    return decorator

def clear_cache():
    """Tüm önbelleği temizler"""
    global _cache
    _cache = {}

def get_auth_header(token):
    """API istekleri için Authorization header'ını oluşturur"""
    if not token:
        logger.error("API token bulunamadı")
        return {}
    return {"Authorization": token}

def convert_docker_url_to_browser_url(url):
    """Docker içindeki URL'yi tarayıcıda çalışacak şekilde dönüştürür"""
    # Docker ve tarayıcı için CDN API URL'lerini al
    docker_cdn_api_url = os.environ.get('DOCKER_CDN_API_URL', 'http://flask:7545')
    browser_cdn_api_url = os.environ.get('BROWSER_CDN_API_URL', 'http://localhost:7545')
    
    # Docker URL'sini tarayıcı URL'sine dönüştür
    if docker_cdn_api_url in url:
        url = url.replace(docker_cdn_api_url, browser_cdn_api_url)
    
    # Domain adlarını da kontrol et ve değiştir
    if 'flask:7545' in url:
        url = url.replace('flask:7545', 'cdn.craftergarage.com')
    
    return url

@cache_result(timeout=60)
def get_collections_from_api(token=None):
    """CDN API'den koleksiyonları alır"""
    if not token:
        logger.error("API token bulunamadı")
        return []
    
    try:
        response = requests.get(
            f"{settings.CDN_API_URL}/list_collections",
            params={"token": token}
        )
        if response.status_code == 200:
            return response.json().get('collections', [])
        else:
            logger.error(f"Koleksiyonlar alınamadı: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Koleksiyonlar alınamadı: {str(e)}")
        return []

@cache_result(timeout=30)
def get_files_from_api(token=None, collection=None, page=1, per_page=100):
    """CDN API'den dosyaları alır"""
    if not token:
        logger.error("API token bulunamadı")
        return {"files": [], "total": 0}
    
    try:
        if collection:
            url = f"{settings.CDN_API_URL}/list_collection/{collection}"
        else:
            url = f"{settings.CDN_API_URL}/list_all"
        
        params = {
            "token": token,
            "page": page,
            "per_page": per_page
        }
        
        response = requests.get(
            url,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # URL'leri tarayıcıda çalışacak şekilde dönüştür
            if 'files' in data:
                data['files'] = [convert_docker_url_to_browser_url(file_url) for file_url in data['files']]
            
            return data
        else:
            logger.error(f"Dosyalar alınamadı: {response.text}")
            return {"files": [], "total": 0}
    except Exception as e:
        logger.error(f"Dosyalar alınamadı: {str(e)}")
        return {"files": [], "total": 0}

def create_collection(name):
    """CDN klasöründe yeni bir koleksiyon (klasör) oluşturur"""
    try:
        # Önbelleği temizle
        clear_cache()
        return True
    except Exception as e:
        logger.error(f"Koleksiyon oluşturulamadı: {str(e)}")
        return False

def api_create_collection(name, token=None):
    """API ile yeni bir koleksiyon oluşturur"""
    if not token:
        logger.error("API token bulunamadı")
        return {"success": False, "error": "API token bulunamadı"}
    
    try:
        response = requests.post(
            f"{settings.CDN_API_URL}/create_collection",
            json={"name": name},
            params={"token": token}
        )
        
        if response.status_code == 201:
            # Önbelleği temizle
            clear_cache()
            return response.json()
        else:
            logger.error(f"Koleksiyon oluşturulamadı: {response.text}")
            return {"success": False, "error": response.text}
    except Exception as e:
        logger.error(f"Koleksiyon oluşturulamadı: {str(e)}")
        return {"success": False, "error": str(e)}

def delete_collection(name):
    """CDN klasöründen bir koleksiyonu (klasörü) siler"""
    try:
        collection_path = os.path.join(settings.CDN_FOLDER, name)
        if os.path.exists(collection_path) and os.path.isdir(collection_path):
            shutil.rmtree(collection_path)
            # Önbelleği temizle
            clear_cache()
            return True
        return False
    except Exception as e:
        logger.error(f"Koleksiyon silinemedi: {str(e)}")
        return False

def upload_file(file, collection=None):
    """Dosyayı CDN klasörüne yükler"""
    try:
        if collection:
            target_dir = os.path.join(settings.CDN_FOLDER, collection)
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = settings.CDN_FOLDER
        
        file_path = os.path.join(target_dir, file.name)
        
        # Dosya adı çakışması kontrolü
        if os.path.exists(file_path):
            name, ext = os.path.splitext(file.name)
            counter = 1
            while os.path.exists(file_path):
                new_name = f"{name}_{counter}{ext}"
                file_path = os.path.join(target_dir, new_name)
                counter += 1
        
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        return {
            "success": True,
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": os.path.getsize(file_path)
        }
    except Exception as e:
        logger.error(f"Dosya yüklenemedi: {str(e)}")
        return {"success": False, "error": str(e)}

def delete_file(file_path):
    """CDN klasöründen bir dosyayı siler"""
    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Dosya silinemedi: {str(e)}")
        return False

def rename_file(old_path, new_name):
    """CDN klasöründeki bir dosyayı yeniden adlandırır"""
    try:
        if os.path.exists(old_path) and os.path.isfile(old_path):
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            
            # Dosya adı çakışması kontrolü
            if os.path.exists(new_path) and old_path != new_path:
                name, ext = os.path.splitext(new_name)
                counter = 1
                while os.path.exists(new_path):
                    new_name_with_counter = f"{name}_{counter}{ext}"
                    new_path = os.path.join(directory, new_name_with_counter)
                    counter += 1
            
            os.rename(old_path, new_path)
            return {"success": True, "path": new_path}
        return {"success": False, "error": "Dosya bulunamadı"}
    except Exception as e:
        logger.error(f"Dosya yeniden adlandırılamadı: {str(e)}")
        return {"success": False, "error": str(e)}

def move_file(old_path, new_collection=None):
    """CDN klasöründeki bir dosyayı başka bir koleksiyona taşır"""
    try:
        if os.path.exists(old_path) and os.path.isfile(old_path):
            file_name = os.path.basename(old_path)
            
            if new_collection:
                target_dir = os.path.join(settings.CDN_FOLDER, new_collection)
                os.makedirs(target_dir, exist_ok=True)
            else:
                target_dir = settings.CDN_FOLDER
            
            new_path = os.path.join(target_dir, file_name)
            
            # Dosya adı çakışması kontrolü
            if os.path.exists(new_path) and old_path != new_path:
                name, ext = os.path.splitext(file_name)
                counter = 1
                while os.path.exists(new_path):
                    new_name = f"{name}_{counter}{ext}"
                    new_path = os.path.join(target_dir, new_name)
                    counter += 1
            
            shutil.move(old_path, new_path)
            return {"success": True, "path": new_path}
        return {"success": False, "error": "Dosya bulunamadı"}
    except Exception as e:
        logger.error(f"Dosya taşınamadı: {str(e)}")
        return {"success": False, "error": str(e)}

def get_file_info(file_path):
    """Dosya bilgilerini döndürür"""
    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            name = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            
            # Koleksiyon adını belirle
            rel_path = os.path.relpath(file_path, settings.CDN_FOLDER)
            parts = Path(rel_path).parts
            collection = parts[0] if len(parts) > 1 else None
            
            return {
                "name": name,
                "path": file_path,
                "collection": collection,
                "size": size
            }
        return None
    except Exception as e:
        logger.error(f"Dosya bilgileri alınamadı: {str(e)}")
        return None

def scan_cdn_folder():
    """CDN klasörünü tarar ve tüm dosya ve koleksiyonları döndürür"""
    collections = []
    files = []
    
    try:
        # Ana dizindeki dosyaları tara
        for item in os.listdir(settings.CDN_FOLDER):
            item_path = os.path.join(settings.CDN_FOLDER, item)
            
            if os.path.isdir(item_path):
                collections.append(item)
                
                # Koleksiyon içindeki dosyaları tara
                try:
                    # Sadece ilk 10 dosyayı tara (performans için)
                    for file in list(os.listdir(item_path))[:10]:
                        file_path = os.path.join(item_path, file)
                        if os.path.isfile(file_path):
                            file_info = get_file_info(file_path)
                            if file_info:
                                files.append(file_info)
                except Exception as e:
                    logger.error(f"Koleksiyon içindeki dosyalar taranamadı: {str(e)}")
            elif os.path.isfile(item_path):
                file_info = get_file_info(item_path)
                if file_info:
                    files.append(file_info)
        
        return {"collections": collections, "files": files}
    except Exception as e:
        logger.error(f"CDN klasörü taranamadı: {str(e)}")
        return {"collections": [], "files": []}

# Yeni API fonksiyonları
def api_upload_file(file, collection=None, token=None):
    """CDN API kullanarak dosya yükleme"""
    try:
        if not token:
            logger.error("API token bulunamadı")
            return {"success": False, "error": "API token bulunamadı"}
        
        url = f"{settings.CDN_API_URL}/file_upload"
        
        # Multipart/form-data isteği için dosya ve koleksiyon bilgilerini hazırla
        files = {'file': (file.name, file, file.content_type)}
        data = {}
        if collection:
            data['collection'] = collection
        
        # API isteği gönder
        response = requests.post(
            url,
            files=files,
            data=data,
            params={"token": token}
        )
        
        if response.status_code == 201:
            # Önbelleği temizle
            clear_cache()
            return response.json()
        else:
            logger.error(f"Dosya yüklenemedi: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        logger.error(f"Dosya yüklenemedi: {str(e)}")
        return {"success": False, "error": str(e)}

def api_bulk_upload(files, collection=None, token=None):
    """CDN API kullanarak toplu dosya yükleme"""
    try:
        if not token:
            logger.error("API token bulunamadı")
            return {"success": False, "error": "API token bulunamadı"}
        
        url = f"{settings.CDN_API_URL}/bulk_upload"
        
        # Multipart/form-data isteği için dosyaları ve koleksiyon bilgilerini hazırla
        files_list = []
        for f in files:
            files_list.append(('files[]', (f.name, f, f.content_type)))
        
        data = {}
        if collection:
            data['collection'] = collection
        
        logger.info(f"API isteği gönderiliyor: URL={url}, Collection={collection}, Files={[f.name for f in files]}")
        
        # API isteği gönder
        response = requests.post(
            url,
            files=files_list,
            data=data,
            params={"token": token}
        )
        
        if response.status_code == 201:
            # Önbelleği temizle
            clear_cache()
            return response.json()
        else:
            logger.error(f"Dosyalar yüklenemedi: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        logger.error(f"Dosyalar yüklenemedi: {str(e)}")
        return {"success": False, "error": str(e)}

def api_delete_file(file_path, token=None):
    """CDN API kullanarak dosya silme"""
    try:
        if not token:
            logger.error("API token bulunamadı")
            return False
        
        url = f"{settings.CDN_API_URL}/delete_file"
        
        # API isteği gönder
        response = requests.post(
            url,
            json={"path": file_path},
            params={"token": token}
        )
        
        if response.status_code == 200:
            # Önbelleği temizle
            clear_cache()
            return True
        else:
            logger.error(f"Dosya silinemedi: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Dosya silinemedi: {str(e)}")
        return False

def api_delete_collection(collection_name, token=None):
    """CDN API kullanarak koleksiyon silme"""
    try:
        if not token:
            logger.error("API token bulunamadı")
            return False
        
        url = f"{settings.CDN_API_URL}/delete_collection"
        
        # API isteği gönder
        response = requests.post(
            url,
            json={"name": collection_name},
            params={"token": token}
        )
        
        if response.status_code == 200:
            # Önbelleği temizle
            clear_cache()
            return True
        else:
            logger.error(f"Koleksiyon silinemedi: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Koleksiyon silinemedi: {str(e)}")
        return False

def api_update_collection(old_name, new_name, token=None):
    """CDN API kullanarak koleksiyon güncelleme"""
    try:
        if not token:
            logger.error("API token bulunamadı")
            return {"success": False, "error": "API token bulunamadı"}
        
        url = f"{settings.CDN_API_URL}/update_collection"
        
        # API isteği gönder
        response = requests.post(
            url,
            json={"old_name": old_name, "new_name": new_name},
            params={"token": token}
        )
        
        if response.status_code == 200:
            # Önbelleği temizle
            clear_cache()
            return response.json()
        else:
            logger.error(f"Koleksiyon güncellenemedi: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        logger.error(f"Koleksiyon güncellenemedi: {str(e)}")
        return {"success": False, "error": str(e)} 
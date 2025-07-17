"""
Bu dosya sadece frontend gösterimi için model sınıfları içerir.
Gerçek veritabanı işlemleri yapılmaz, tüm veriler CDN API'den alınır.
"""

class CDNFile:
    """CDN'deki dosyaları temsil eden sınıf - Sadece frontend gösterimi için"""
    
    def __init__(self, name, path, collection=None, size=0):
        self.name = name
        self.path = path
        self.collection = collection
        self.size = size
    
    @property
    def file_type(self):
        """Dosya uzantısını döndürür"""
        import os
        _, ext = os.path.splitext(self.name)
        return ext.lower().replace('.', '')
    
    @property
    def is_image(self):
        """Dosyanın resim olup olmadığını kontrol eder"""
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.file_type.lower() in image_extensions
    
    @property
    def size_formatted(self):
        """Dosya boyutunu okunaklı formatta döndürür"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.2f} {unit}"
            size /= 1024

class Collection:
    """CDN'deki koleksiyonları temsil eden sınıf - Sadece frontend gösterimi için"""
    
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        
    @property
    def slug(self):
        """Koleksiyon adından slug oluşturur"""
        from django.utils.text import slugify
        return slugify(self.name)

class UploadSession:
    """Toplu yükleme işlemlerini izlemek için sınıf - Sadece frontend gösterimi için"""
    
    def __init__(self, collection_name, total_files=0, processed_files=0, failed_files=0, status='pending'):
        self.collection_name = collection_name
        self.total_files = total_files
        self.processed_files = processed_files
        self.failed_files = failed_files
        self.status = status
    
    @property
    def progress(self):
        """İlerleme yüzdesini döndürür"""
        if self.total_files == 0:
            return 0
        return int((self.processed_files / self.total_files) * 100)

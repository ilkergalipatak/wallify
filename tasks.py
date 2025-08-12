import os
import time
import logging
from celery import Celery
from celery.schedules import crontab
import config
from models import Base, File, Collection, User
from auth import AuthService
from cdn_service import CDNService
from datetime import datetime

# Celery uygulamasını oluştur
celery_app = Celery('wallify_tasks')

# Celery konfigürasyonu
celery_app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 dakika
    task_soft_time_limit=25 * 60,  # 25 dakika
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy loading için global değişkenler
_engine = None
_Session = None
_auth_service = None
_cdn_service = None

def get_database_session():
    """Veritabanı session'ını lazy loading ile oluştur"""
    global _engine, _Session
    
    if _Session is None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config import DATABASE_URL
            from models import Base
            
            _engine = create_engine(DATABASE_URL)
            Base.metadata.create_all(_engine)
            _Session = sessionmaker(bind=_engine)
            logger.info("Database session created successfully")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    return _Session

def get_auth_service():
    """Auth service'i lazy loading ile oluştur"""
    global _auth_service
    
    if _auth_service is None:
        try:
            from auth import AuthService
            session = get_database_session()
            if session:
                _auth_service = AuthService(session)
                logger.info("Auth service created successfully")
        except Exception as e:
            logger.error(f"Auth service initialization error: {e}")
    
    return _auth_service

def get_cdn_service():
    """CDN service'i lazy loading ile oluştur"""
    global _cdn_service
    
    if _cdn_service is None:
        try:
            from cdn_service import CDNService
            session = get_database_session()
            auth_service = get_auth_service()
            if session and auth_service:
                _cdn_service = CDNService(session, auth_service)
                logger.info("CDN service created successfully")
        except Exception as e:
            logger.error(f"CDN service initialization error: {e}")
    
    return _cdn_service

@celery_app.task(bind=True)
def process_image_async(self, file_id, user_id):
    """Asenkron resim işleme"""
    try:
        logger.info(f"Starting async image processing for file_id: {file_id}")
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        # Resim işleme simülasyonu
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})
        time.sleep(2)
        
        self.update_state(state='PROGRESS', meta={'current': 50, 'total': 100})
        time.sleep(2)
        
        self.update_state(state='PROGRESS', meta={'current': 100, 'total': 100})
        
        logger.info(f"Async image processing completed for file_id: {file_id}")
        return {'status': 'completed', 'file_id': file_id, 'processed_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error in process_image_async: {e}")
        raise

@celery_app.task(bind=True)
def bulk_process_images(self, file_ids, user_id):
    """Toplu resim işleme"""
    try:
        logger.info(f"Starting bulk image processing for {len(file_ids)} files")
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        results = []
        total_files = len(file_ids)
        
        for i, file_id in enumerate(file_ids):
            self.update_state(
                state='PROGRESS', 
                meta={'current': i, 'total': total_files, 'current_file': file_id}
            )
            
            # Her dosya için işleme simülasyonu
            time.sleep(1)
            results.append({'file_id': file_id, 'status': 'processed'})
        
        logger.info(f"Bulk image processing completed for {len(file_ids)} files")
        return {'status': 'completed', 'results': results, 'processed_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error in bulk_process_images: {e}")
        raise

@celery_app.task
def generate_thumbnails(file_id, sizes=None):
    """Thumbnail oluşturma"""
    try:
        logger.info(f"Generating thumbnails for file_id: {file_id}")
        
        if sizes is None:
            sizes = ['100x100', '200x200', '300x300']
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        # Thumbnail oluşturma simülasyonu
        time.sleep(3)
        
        logger.info(f"Thumbnails generated for file_id: {file_id}")
        return {'status': 'completed', 'file_id': file_id, 'thumbnails': sizes}
        
    except Exception as e:
        logger.error(f"Error in generate_thumbnails: {e}")
        raise

@celery_app.task
def cleanup_orphaned_files():
    """Yetim dosyaları temizleme"""
    try:
        logger.info("Starting orphaned files cleanup")
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        # Temizlik simülasyonu
        time.sleep(5)
        
        logger.info("Orphaned files cleanup completed")
        return {'status': 'completed', 'cleaned_files': 0, 'cleaned_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error in cleanup_orphaned_files: {e}")
        raise

@celery_app.task
def update_collection_stats():
    """Koleksiyon istatistiklerini güncelleme"""
    try:
        logger.info("Starting collection stats update")
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        # İstatistik güncelleme simülasyonu
        time.sleep(3)
        
        logger.info("Collection stats update completed")
        return {'status': 'completed', 'updated_collections': 0, 'updated_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error in update_collection_stats: {e}")
        raise

@celery_app.task
def optimize_images():
    """Resim optimizasyonu"""
    try:
        logger.info("Starting image optimization")
        
        cdn_service = get_cdn_service()
        if not cdn_service:
            raise Exception("CDN service not available")
        
        # Optimizasyon simülasyonu
        time.sleep(10)
        
        logger.info("Image optimization completed")
        return {'status': 'completed', 'optimized_images': 0, 'optimized_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error in optimize_images: {e}")
        raise

# Periyodik görevleri ayarla
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Günlük temizlik - her gün saat 02:00'de
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_orphaned_files.s(),
        name='daily-cleanup'
    )
    
    # Saatlik koleksiyon istatistikleri - her saat başı
    sender.add_periodic_task(
        crontab(minute=0),
        update_collection_stats.s(),
        name='hourly-stats'
    )
    
    # Günlük resim optimizasyonu - her gün saat 03:00'de
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        optimize_images.s(),
        name='daily-optimization'
    )

if __name__ == '__main__':
    celery_app.start() 
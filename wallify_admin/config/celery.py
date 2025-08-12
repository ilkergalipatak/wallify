import os
from celery import Celery

# Django ayarlarını Celery için ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('wallify_admin')

# Django ayarlarından Celery konfigürasyonunu yükle
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django uygulamalarından görevleri otomatik yükle
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campaign_builder.settings')

app = Celery('campaign_builder')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# backend/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# Read config from Django settings, with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in Django apps
app.autodiscover_tasks()

# Optional: define a debug task for testing
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

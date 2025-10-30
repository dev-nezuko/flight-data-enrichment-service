import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")
# Celery reads the CELERY_* names from Django settings (broker URL, serializers).
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

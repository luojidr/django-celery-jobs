import os

# Set DJANGO_SETTINGS_MODULE is important
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'celery_jobs_demo.settings')

from celery_jobs_demo.core.djcelery_helper.djcelery import app as celery_app

__all__ = ["celery_app"]

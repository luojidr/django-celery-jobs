from __future__ import absolute_import

import os

from celery import Celery
from celery import platforms
from django.conf import ENVIRONMENT_VARIABLE

__all__ = ["app"]

# Specifying the settings here means the celery command line program will know where your Django project is.
# This statement must always appear before the app instance is created, which is what we do next:
django_settings_module = os.getenv(ENVIRONMENT_VARIABLE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', django_settings_module)

app = Celery('testCelery')
platforms.C_FORCE_ROOT = True

app.conf.broker_url = 'amqp://admin:admin013431_Prd@47.96.113.102:5672/%2Ftest'
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
app.conf.timezone = "Asia/Shanghai"
app.conf.enable_utc = False

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))  # dumps its own request information


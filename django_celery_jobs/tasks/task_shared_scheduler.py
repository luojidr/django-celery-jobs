import logging
import traceback

from django.db.models import Q
from django.utils import timezone

from ..jobScheduler.core.celery.utils import get_celery_app
from ..jobScheduler.scheduler import default_scheduler
from ..models import CeleryNativeTaskModel, JobPeriodicModel, BeatPeriodicTaskModel

celery_app = get_celery_app()
logger = logging.getLogger('celery.task')


@celery_app.task(ignore_result=False)
def shared_scheduler(**kwargs):
    print('shared_schedule to test')

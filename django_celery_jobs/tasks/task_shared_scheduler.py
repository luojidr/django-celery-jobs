import logging
import traceback

from django.db.models import Q

from ..jobScheduler.core.celery.utils import get_celery_app
from ..jobScheduler.scheduler import default_scheduler
from ..models import CeleryNativeTaskModel

celery_app = get_celery_app()
logger = logging.getLogger('celery.task')


@celery_app.task(ignore_result=False)
def sync_celery_native_tasks(**kwargs):
    try:
        task_list = []
        native_tasks = default_scheduler.get_celery_native_tasks()

        for task in native_tasks:
            task_list.append(task['task'])
            CeleryNativeTaskModel.create_or_update_native_task(**task)

        q = Q(task__in=task_list, is_del=False)
        CeleryNativeTaskModel.objects.filter(~q).update(is_del=True, desc='自动监控->停止')
    except Exception as e:
        logger.warning('sync_celery_native_tasks error: %s', e)
        logger.error(traceback.format_exc())


@celery_app.task(ignore_result=False)
def shared_scheduler(**kwargs):
    print('shared_schedule')

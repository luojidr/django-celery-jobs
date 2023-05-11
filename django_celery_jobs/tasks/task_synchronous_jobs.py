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


@celery_app.task
def watch_periodic_tasks(**kwargs):
    fields = ['id', 'title', 'periodic_task_id', 'deadline_run_time']
    periodic_tasks = JobPeriodicModel.objects.filter(is_del=False, is_enabled=True).values(*fields)
    logger.info("Watch Job heartbeat => periodic task count: %s", len(periodic_tasks))

    for task in periodic_tasks:
        try:
            job_id = task['id']
            job_title = task['title']
            deadline = task['deadline_run_time']
            beat_task_id = task['periodic_task_id']

            if not deadline:
                continue

            deadline_run_time = timezone.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
            if deadline_run_time < timezone.datetime.now():
                logger.info('PeriodicJob<%s> Deadline Run Time: %s', job_title, deadline)

                BeatPeriodicTaskModel.objects.filter(id=beat_task_id).update(enabled=False)
                JobPeriodicModel.objects.filter(id=job_id).update(remark='自动监控->停止')
        except Exception as e:
            logger.warning('watch_periodic_tasks error: %s', e)
            logger.error(traceback.format_exc())

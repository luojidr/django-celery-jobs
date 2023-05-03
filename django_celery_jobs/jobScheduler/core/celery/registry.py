import logging
from datetime import datetime

from django_celery_beat.models import PeriodicTask
from celery.signals import beat_init, celeryd_init, task_internal_error, import_modules

from .utils import autodiscover_tasks
from django_celery_jobs.jobScheduler.trigger.cron import CronTrigger
from django_celery_jobs.tasks.task_shared_scheduler import sync_celery_native_tasks

logger = logging.getLogger("celery.worker")


@celeryd_init.connect
def load_worker(sender, instance, conf, options, **kwargs):
    logging.warning("Sender<%s> instance: %s, conf: %s, options: %s", sender, instance, conf, options)

    if not conf.result_backend:
        logger.warning("Setting `result_backend` is strongly recommended.")

    # Auto sync celery task to database
    trigger = CronTrigger.from_crontab('* * * * *')  # Every minute
    cron = trigger.get_trigger_schedule()

    name = sync_celery_native_tasks.name
    beat_task = PeriodicTask.objects.filter(task=name, enabled=True).first()

    if not beat_task:
        PeriodicTask.objects.create(name=name, task=name, crontab_id=cron['crontab_id'])


@beat_init.connect
def load_beat(sender, **kwargs):
    logging.warning('BeatScheduler must be injected first, now: %s', datetime.now())
    logging.warning('BeatScheduler => sender: %s, kwargs: %s', sender, kwargs)


@import_modules.connect
def discover_tasks(sender, **kwargs):
    logging.warning('discover_tasks => sender: %s, kwargs: %s, now: %s', sender, kwargs, datetime.now())

    autodiscover_tasks()


@task_internal_error.connect
def handle_task_internal_error(sender, task_id, args, kwargs, request, einfo, **kw):
    """ Handle errors in tasks by signal, that is not internal logic error in task func code.
        Because the result of a failed task execution is stored in result_backend
    """
    logging.warning("Handle task err => sender<%s> was error: %s at task<%s>", sender, einfo, task_id)
    logger.error("TaskId: %s, args: %s, kwargs: %s, request: %s", task_id, args, kwargs, request)

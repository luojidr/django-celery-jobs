import logging
from datetime import datetime

from celery.signals import beat_init, celeryd_init, task_internal_error

from .util import find_tasks

logger = logging.getLogger("celery.worker")


@celeryd_init.connect
def load_worker(sender, instance, conf, options, **kwargs):
    logging.warning("Sender<%s> instance: %s, conf: %s, options: %s", sender, instance, conf, options)

    if not conf.result_backend:
        logger.warning("Setting `result_backend` is strongly recommended.")

    find_tasks()


@beat_init.connect
def load_beat(sender, **kwargs):
    logging.warning('BeatScheduler must be injected first, now: %s', datetime.now())
    logging.warning('BeatScheduler => sender: %s, kwargs: %s', sender, kwargs)

    find_tasks()

    from django_celery_beat.schedulers import DatabaseScheduler
    from django_celery_jobs.jobScheduler.core.celery.patch import BeatScheduler

    DatabaseScheduler._schedule_changed = DatabaseScheduler.schedule_changed
    DatabaseScheduler.schedule_changed = BeatScheduler.schedule_changed


@task_internal_error.connect
def handle_task_internal_error(sender, task_id, args, kwargs, request, einfo, **kw):
    """ Handle errors in tasks by signal, that is not internal logic error in task func code.
        Because the result of a failed task execution is stored in result_backend
    """
    logging.warning("Handle task err => sender<%s> was error: %s at task<%s>", sender, einfo, task_id)
    logger.error("TaskId: %s, args: %s, kwargs: %s, request: %s", task_id, args, kwargs, request)

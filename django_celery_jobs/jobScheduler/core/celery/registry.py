import logging

from celery.signals import beat_init, celeryd_init, setup_logging, task_internal_error

from .util import find_tasks

logger = logging.getLogger("celery.worker")


@celeryd_init.connect
def register_tasks_by_worker(sender, instance, conf, options, **kwargs):
    logging.warning("Sender<%s> instance: %s, conf: %s, options: %s", sender, instance, conf, options)

    if not conf.result_backend:
        logger.warning("Setting `result_backend` is strongly recommended.")

    find_tasks()


@beat_init.connect
def register_tasks_by_beat(sender, **kwargs):
    logging.warning('scheduler_middleware => sender: %s, kwargs: %s', sender, kwargs)
    find_tasks()


@setup_logging.connect
def inject_database_scheduler(**kwargs):
    logging.warning('DatabaseScheduler must be injected first.')

    from django_celery_beat.schedulers import DatabaseScheduler
    from django_celery_jobs.jobScheduler.core.celery.patch import MyScheduler

    DatabaseScheduler._schedule_changed = DatabaseScheduler.schedule_changed
    DatabaseScheduler.schedule_changed = MyScheduler.schedule_changed


@task_internal_error.connect
def handle_task_internal_error(sender, task_id, args, kwargs, request, einfo, **kw):
    """ Handle errors in tasks by signal, that is not internal logic error in task func code.
        Because the result of a failed task execution is stored in result_backend
    """
    logging.warning("Handle task err => sender<%s> was error: %s at task<%s>", sender, einfo, task_id)
    logger.error("TaskId: %s, args: %s, kwargs: %s, request: %s", task_id, args, kwargs, request)

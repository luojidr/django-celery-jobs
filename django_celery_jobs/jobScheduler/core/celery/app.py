from __future__ import absolute_import

import logging
import traceback

from celery import Celery
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from .util import handle_task_router

logger = logging.getLogger("celery.worker")


class CeleryAppDispatcher:
    APPS_CACHE = {}

    def __init__(self, scheduler, entry, **kwargs):
        self.entry = entry
        self.scheduler = scheduler

    def get_task(self):
        job_obj = self._get_job()
        config_obj = job_obj.config

        if config_obj.category != 1:
            raise ValueError("JobConfigModel<id:%s> is not a broker config" % config_obj.id)

        celery_name = 'Celery:{0.host}:{0.virtual}'.format(config_obj)
        if celery_name not in self.APPS_CACHE:
            celery_app = Celery(main=celery_name, broker=config_obj.as_url())
            self.APPS_CACHE[celery_name] = celery_app

            # Clean existed task
            for name in list(celery_app.tasks.keys()):
                celery_app.tasks.unregister(name)
        else:
            celery_app = self.APPS_CACHE[celery_name]

        func = job_obj.compile_task_func()
        task_name = func.__name__

        if task_name in celery_app.tasks:
            return celery_app.tasks[task_name]

        task = celery_app.task(func, name=task_name)
        celery_app.tasks.register(task)
        handle_task_router(task=task, app=celery_app)

        return task

    def _get_job(self, name=None, silent=True):
        from django_celery_beat.models import PeriodicTask

        task_name = name or self.entry.task
        try:
            periodic_task_obj = PeriodicTask.objects.get(name=task_name)
            job_queryset = periodic_task_obj.periodic_task.select_related('config').all()

            if len(job_queryset) > 1:
                raise MultipleObjectsReturned('PeriodicJobModel<name:%s> must one' % task_name)

            if not job_queryset:
                raise ObjectDoesNotExist('PeriodicJobModel<name:%s> does not exist' % task_name)

            return job_queryset[0]
        except Exception:
            if silent:
                logger.error(traceback.format_exc())

    def is_default_app(self, name):
        return not bool(self._get_job(name=name, silent=False))

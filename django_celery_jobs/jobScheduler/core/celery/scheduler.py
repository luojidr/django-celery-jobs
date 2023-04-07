import sys
import uuid
import string
import random
import logging
import platform
import traceback
from datetime import datetime

from celery.beat import _evaluate_entry_args, _evaluate_entry_kwargs
from celery.utils import cached_property
from celery.schedules import schedstate

from django.utils import timezone
from django.db.models.base import ModelBase
from django.core.cache import caches
from django.core.cache.backends.redis import RedisCache

from django_celery_beat.schedulers import DatabaseScheduler

from .app import CeleryAppDispatcher
from django_celery_jobs import models

logger = logging.getLogger("celery.worker")


class ModelDict(dict):
    def __getattr__(self, name):
        if name not in self:
            raise AttributeError('No `%s` attribute' % name)

        return self[name]


class SyncScheduledJob:
    on_finalized = False
    Models = ModelDict()
    SYNC_PERIODIC_JOB_CACHE = {}

    def __init__(self, scheduler):
        self.scheduler = scheduler

    def __new__(cls, *args, **kwargs):
        if not cls.on_finalized:
            app_name = __name__.split('.', 1)[0]

            for key, model in models.__dict__.items():
                if key.startswith('_') or key[0].islower():
                    continue

                if not isinstance(model, ModelBase):
                    continue

                meta = model._meta
                if meta.app_label != app_name or meta.abstract:
                    continue

                model_name = meta.object_name
                cls.Models[model_name.split('Model')[0]] = model

            cls.on_finalized = True

        return object.__new__(cls)

    def get_periodic_jobs(self):
        job_ids = [item['id'] for item in self.SYNC_PERIODIC_JOB_CACHE.values()]
        queryset = self.Models.PeriodicJob.get_enabled_tasks().exclude(id__in=job_ids).all()

        return queryset

    def sync_all_schedules(self, **kwargs):
        job_ids = [item['id'] for item in self.SYNC_PERIODIC_JOB_CACHE.values()]
        queryset = self.Models.PeriodicJob.get_enabled_tasks()

        try:
            enable_queryset = queryset.filter(**kwargs).exclude(id__in=job_ids).all()

            for job_obj in enable_queryset:
                self._sync_one_schedule(periodic_job=job_obj)
        except Exception as e:
            logger.error("[%s] >>> SyncJobToSchedule.sync_all_schedules err: %s", __name__, e)
            logger.error(traceback.format_exc())

    def _sync_one_schedule(self, periodic_job):
        job_pk = periodic_job.id

        if job_pk not in self.SYNC_PERIODIC_JOB_CACHE:
            func = periodic_job.compile_task_func()
            if not func: return

            task = self.scheduler.app.task(func, name=func.__name__)
            self.scheduler.app.tasks.register(task)  # Register task to celery_app.apps.tasks

            task_name = task.name.rsplit('.', 1)[-1]
            # entry: celery_app.conf.beat_schedule
            entry_fields = dict(
                task=task_name, args=(), kwargs={},
                schedule=periodic_job.crontab.schedule,
                options={'expire_seconds': None},
            )

            update_attrs = dict()
            entry = self.scheduler.Entry.from_entry(task_name, app=self.scheduler.app, **entry_fields)

            if not periodic_job.func_name.strip():
                update_attrs['func_name'] = func.__name__

            if not periodic_job.periodic_task:
                update_attrs['periodic_task'] = entry.model
            periodic_job.save_attrs(**update_attrs)

            self.SYNC_PERIODIC_JOB_CACHE[job_pk] = dict(id=job_pk, title=periodic_job.title)


class BeatScheduler(DatabaseScheduler):
    @cached_property
    def redis_conn(self):
        try:
            from django_redis import get_redis_connection

            _cache = get_redis_connection()
        except (ModuleNotFoundError, NotImplementedError):
            # default is redis, use raw redis
            djcache = caches['default']
            if not isinstance(djcache, RedisCache):
                try:
                    djcache = caches['redis']
                except AttributeError:
                    djcache = None

            if djcache:
                return djcache._cache.get_client(None, write=True)

        logger.error('Fuck, redis client not find from settings.CACHES')

    def is_due(self, entry):
        sched_state = (_, next_run_time) = entry.is_due()
        uniq_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(22))

        # Not distributed redis lock
        if not self.redis_conn:
            return sched_state

        # Multi scheduler to run
        key = entry.task
        default_expire = (int(next_run_time) - 1) * 1000  # milliseconds
        log_args = [platform.system(), platform.node(), key]

        # Important:
        # Multiple schedulers are executed periodically when they are started, although each scheduler
        # may not trigger at the same time.
        # Because each scheduler starts at different times, there is a time offset, however,
        # distributed locks are used to ensure that only one scheduler is triggered in during `wakeup_interval`
        try:
            if default_expire > 0 and self.redis_conn.set(key, uniq_val, px=default_expire, nx=True):
                logger.warning("%s<%s> apply scheduled<%s> succeed, now: %s", *(log_args + [datetime.now()]))
                return entry.is_due()
        except Exception as e:
            logger.error(traceback.format_exc())

        # logger.warning("%s<%s> apply scheduled<%s> passed, now: %s", *(log_args + [datetime.now()]))
        return schedstate(is_due=False, next=next_run_time)

    def apply_async(self, entry, producer=None, advance=True, **kwargs):
        entry = self.reserve(entry) if advance else entry
        task = self.app.tasks.get(entry.task)

        entry_args = _evaluate_entry_args(entry.args)
        entry_kwargs = _evaluate_entry_kwargs(entry.kwargs)

        log_args = (__name__, task and task.name, datetime.now())
        logger.warning("[%s] >>> task<%s> is scheduled, now: %s", *log_args)

        # The timing message is sent to different MQ servers
        dispatcher = CeleryAppDispatcher(self, entry=entry)

        run_date = timezone.now()
        scheduled_kw = dict(sched_id=str(uuid.uuid1()).replace('-', ''), name=entry.task,
                            periodic_task_id=entry.model.id, is_success=True, run_date=run_date)

        try:
            if task and not dispatcher.is_default_app(name=entry.task):
                dispatch_task = dispatcher.get_task()
                return dispatch_task.apply_async(entry_args, entry_kwargs, producer=None, **entry.options)
            else:
                return super().apply_async(entry, producer, advance, **kwargs)
        except Exception as e:
            exc_info = traceback.format_exc()
            scheduled_kw.update(is_success=False, traceback=exc_info[-2800:])
        finally:
            SyncScheduledJob.Models.JobScheduledResult.add_result(**scheduled_kw)

    def schedule_changed(self):
        is_changed = super().schedule_changed()
        SyncScheduledJob(self).sync_all_schedules()

        return is_changed



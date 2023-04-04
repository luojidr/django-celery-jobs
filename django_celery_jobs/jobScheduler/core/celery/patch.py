import sys
import uuid
import string
import random
import logging
import platform
import traceback
from datetime import datetime

from celery.beat import Scheduler
from celery.beat import SchedulingError
from celery.beat import _evaluate_entry_args, _evaluate_entry_kwargs
from celery.exceptions import reraise
from django.utils import timezone
from celery.utils import cached_property
from celery.schedules import schedstate

from django.core.cache import caches
from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger("celery.worker")
PERIODIC_TASK_CACHE = {}


class MyScheduler(Scheduler):
    @cached_property
    def JobScheduledResult(self):
        from django_celery_jobs.models import JobScheduledResultModel

        return JobScheduledResultModel

    @cached_property
    def PeriodicJob(self):
        from django_celery_jobs.models import PeriodicJobModel

        return PeriodicJobModel

    @classmethod
    def DatabaseScheduler(cls):
        from django_celery_beat.schedulers import DatabaseScheduler

        return DatabaseScheduler

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
        entry.sched_id = str(uuid.uuid1()).replace('-', '')
        sched_state = (_, next_run_time) = entry.is_due()
        uniq_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(22))

        # Not distributed redis lock
        if not self.redis_conn:
            return sched_state

        # Multi scheduler to run
        key = entry.name
        default_expire = (int(next_run_time) - 1) * 1000  # milliseconds
        log_args = [platform.system(), platform.node(), key]

        # Important:
        # Multiple schedulers are executed periodically when they are started, although each scheduler
        # may not trigger at the same time.
        # Because each scheduler starts at different times, there is a time offset, however,
        # distributed locks are used to ensure that only one scheduler is triggered in during `wakeup_interval`
        is_scheduled = False
        run_date = timezone.now()
        scheduled_kw = dict(sched_id=entry.sched_id, name=key,
                            periodic_task_id=entry.model.id, is_success=True, run_date=run_date)

        try:
            if default_expire > 0 and self.redis_conn.set(key, uniq_val, px=default_expire, nx=True):
                is_scheduled = True
                logger.warning("%s<%s> apply scheduled<%s> succeed, now: %s", *(log_args + [datetime.now()]))
                return entry.is_due()
        except Exception as e:
            is_scheduled = True
            exc_info = traceback.format_exc()
            scheduled_kw.update(is_success=False, traceback=exc_info[-2800:])
        finally:
            if is_scheduled:
                self.JobScheduledResult.add_result(**scheduled_kw)

        logger.warning("%s<%s> apply scheduled<%s> passed, now: %s", *(log_args + [datetime.now()]))
        return schedstate(is_due=False, next=next_run_time)

    def apply_async(self, entry, producer=None, advance=True, **kwargs):
        exc_info = ''
        entry = self.reserve(entry) if advance else entry
        task = self.app.tasks.get(entry.task)

        try:
            entry_args = _evaluate_entry_args(entry.args)
            entry_kwargs = _evaluate_entry_kwargs(entry.kwargs)
            if task:
                return task.apply_async(entry_args, entry_kwargs, producer=producer, **entry.options)
            else:
                return self.send_task(entry.task, entry_args, entry_kwargs, producer=producer, **entry.options)
        except Exception as exc:
            exc_info = traceback.format_exc()[-2800:]
            reraise(
                SchedulingError,
                SchedulingError("Couldn't apply scheduled task {0.name}: {exc}".format(entry, exc=exc)),
                sys.exc_info()[2]
            )
        finally:
            self._tasks_since_sync += 1
            if self.should_sync():
                self._do_sync()

            if exc_info:
                self.JobScheduledResult.update_scheduled_result(
                    sched_id=entry.sched_id,
                    traceback=exc_info
                )

    def schedule_changed(self):
        is_changed = self._schedule_changed()

        try:
            cached_ids = [item['id'] for item in PERIODIC_TASK_CACHE.values()]
            enable_queryset = self.PeriodicJob.get_enabled_tasks().exclude(id__in=cached_ids).all()

            for task_obj in enable_queryset:
                self._update_schedule(periodic_task_obj=task_obj)
        except Exception as e:
            logger.error("[%s] >>> schedule_changed err: %s", __name__, e)
            logger.error(traceback.format_exc())

        return is_changed

    def _update_schedule(self, periodic_task_obj):
        task_pk = periodic_task_obj.id

        if task_pk not in PERIODIC_TASK_CACHE:
            func = periodic_task_obj.compile_task_func()
            if not func:
                return

            task = self.app.task(func)
            self.app.tasks.register(task)  # Register task to celery_app.apps.tasks

            task_name = task.name
            # entry: celery_app.conf.beat_schedule
            entry_fields = dict(
                task=task_name, args=(), kwargs={},
                schedule=periodic_task_obj.get_crontab(),
                options={'expire_seconds': None},
            )

            periodic_task_obj.func_name = task_name
            periodic_task_obj.save()

            self.Entry.from_entry(task_name, app=self.app, **entry_fields)
            PERIODIC_TASK_CACHE[task_pk] = dict(id=task_pk, func=func)

    Scheduler.is_due = is_due
    Scheduler.redis_conn = redis_conn
    Scheduler.apply_async = apply_async
    Scheduler._update_schedule = _update_schedule
    Scheduler.PeriodicJob = PeriodicJob
    Scheduler.JobScheduledResult = JobScheduledResult


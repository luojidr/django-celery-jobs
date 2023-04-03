import string
import random
import pkgutil
import logging
import platform
import importlib
import traceback
from datetime import datetime

import sys

from kombu import Queue
from celery import current_app
from celery.app.task import Task
from celery.beat import Scheduler
from celery.signals import beat_init
from celery.utils import cached_property
from celery.schedules import schedstate

from django.core.cache import caches
from django.core.cache.backends.redis import RedisCache

from . import tasks

logger = logging.getLogger("celery.worker")


class MyScheduler(Scheduler):
    @cached_property
    def scheduledModel(self):
        from .models import JobScheduledRecord

        return JobScheduledRecord

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
        key = entry.name
        default_expire = (int(next_run_time) - 1) * 1000  # milliseconds
        log_args = [platform.system(), platform.node(), key]

        # Important:
        # Multiple schedulers are executed periodically when they are started, although each scheduler
        # may not trigger at the same time.
        # Because each scheduler starts at different times, there is a time offset, however,
        # distributed locks are used to ensure that only one scheduler is triggered in during `wakeup_interval`
        is_scheduled = False
        scheduled_kw = dict(name=key, periodic_task_id=entry.model.id, is_success=True, exc_info='')

        try:
            if default_expire > 0 and self.redis_conn.set(key, uniq_val, px=default_expire, nx=True):
                is_scheduled = True
                logger.warning("%s<%s> apply scheduled<%s> succeed, now: %s", *(log_args + [datetime.now()]))
                return entry.is_due()
        except Exception as e:
            is_scheduled = True
            exc_info = traceback.format_exc()
            scheduled_kw.update(is_success=False, exc_info=exc_info[-1900:])
        finally:
            if is_scheduled:
                self.scheduledModel.scheduled_log(**scheduled_kw)

        logger.warning("%s<%s> apply scheduled<%s> passed, now: %s", *(log_args + [datetime.now()]))
        return schedstate(is_due=False, next=next_run_time)

    Scheduler.is_due = is_due
    Scheduler.redis_conn = redis_conn
    Scheduler.scheduledModel = scheduledModel


def update_task_router(task):
    task_name = task.name
    name = task_name.rsplit('.', 1)[-1]
    default_qname = name + '_q'
    default_exchange = name + '_exc'
    default_routing_key = name + '_rk'

    task_queues = current_app.conf.task_queues or []
    task_routes = current_app.conf.task_routes or {}

    for q in task_queues:
        qname = q.name if isinstance(q, Queue) else q

        if qname == default_qname:
            break
    else:
        q = Queue(default_qname, default_exchange, default_routing_key)
        if task_queues:
            current_app.conf.task_queues.append(q)
        else:
            current_app.conf.task_queues = [q]

    for full_task_name, route in task_routes.items():
        q_name = route.get('queue')

        if task_name == full_task_name and q_name == default_qname:
            break
    else:
        route = {task_name: {'queue': default_qname, 'routing_key': default_routing_key}}
        if task_routes:
            current_app.conf.task_routes.update(**route)
        else:
            current_app.conf.task_routes = dict(**route)


@beat_init.connect
def register_tasks(sender, **kwargs):
    task_list = []
    logging.warning('scheduler_middleware => sender: %s, kwargs: %s', sender, kwargs)

    for module_info in pkgutil.iter_modules(tasks.__path__, tasks.__name__ + "."):
        task_name = task_module_path = module_info.name
        filename = task_name.rsplit('.', 1)[-1]

        if filename.startswith('task_'):
            try:
                mod = importlib.import_module(task_module_path)
                names = [k for k in dir(mod) if not k.startswith('_')]

                for name in names:
                    obj = getattr(mod, name)
                    if isinstance(obj, Task):
                        task_list.append(obj.name)
                        update_task_router(obj)
            except (ImportError, ModuleNotFoundError):
                logger.error('import module: %s error.', task_module_path)

    if task_list:
        logger.warning("Task show: \n\t%s", '\n\t'.join(task_list))

    for complete_task_name, task in current_app.tasks.items():
        logger.info('name: %s, task: %s', complete_task_name, task)

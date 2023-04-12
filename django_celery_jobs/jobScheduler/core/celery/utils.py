import logging
import pkgutil
import importlib

from kombu import Queue
from celery import current_app
from celery.app.task import Task
import logging
import importlib
import traceback

from django.conf import settings
from celery import current_app
from celery.exceptions import ImproperlyConfigured

from django_celery_jobs import tasks

logger = logging.getLogger("celery.worker")
_default_app = None


def get_celery_app():
    global _default_app

    if _default_app is not None:
        return _default_app

    try:
        app_path = settings.CELERY_APP
        pkg_name, app_name = app_path.split(":", 1)

        module = importlib.import_module(pkg_name)
        _default_app = getattr(module, app_name, current_app)
    except (AttributeError, ValueError, ModuleNotFoundError):
        logging.error("import celery app is failed")
        logging.error(traceback.format_exc())

        _default_app = current_app

    if _default_app.conf.broker_url is None:
        raise ImproperlyConfigured("Celery instance is empty, recommended set `CELERY_APP`")

    return _default_app


def handle_task_router(task, app=None):
    task_name = task.name
    name = task_name.rsplit('.', 1)[-1]
    celery_app = app or current_app

    default_qname = name + '_q'
    default_exchange = name + '_exc'
    default_routing_key = name + '_rk'

    task_queues = celery_app.conf.task_queues or []
    task_routes = celery_app.conf.task_routes or {}

    for q in task_queues:
        qname = q.name if isinstance(q, Queue) else q

        if qname == default_qname:
            break
    else:
        q = Queue(default_qname, default_exchange, default_routing_key)
        if task_queues:
            celery_app.conf.task_queues.append(q)
        else:
            celery_app.conf.task_queues = [q]

    for full_task_name, route in task_routes.items():
        q_name = route.get('queue')

        if task_name == full_task_name and q_name == default_qname:
            break
    else:
        route = {task_name: {'queue': default_qname, 'routing_key': default_routing_key}}
        if task_routes:
            celery_app.conf.task_routes.update(**route)
        else:
            celery_app.conf.task_routes = dict(**route)


def autodiscover_tasks():
    task_list = []

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
                        handle_task_router(obj)
            except (ImportError, ModuleNotFoundError):
                logger.error('import module: %s error.', task_module_path)

    if task_list:
        logger.warning("Find tasks show: \n\t%s", '\n\t'.join(task_list))

    for complete_task_name, task in current_app.tasks.items():
        logger.info('name: %s, task: %s', complete_task_name, task)

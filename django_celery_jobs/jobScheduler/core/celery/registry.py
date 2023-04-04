import pkgutil
import logging
import importlib

from kombu import Queue
from celery import current_app
from celery.app.task import Task
from celery.signals import beat_init, celeryd_init, setup_logging, task_internal_error

from django_celery_jobs import tasks

logger = logging.getLogger("celery.worker")


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


def find_tasks():
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
                        update_task_router(obj)
            except (ImportError, ModuleNotFoundError):
                logger.error('import module: %s error.', task_module_path)

    if task_list:
        logger.warning("Find tasks show: \n\t%s", '\n\t'.join(task_list))

    for complete_task_name, task in current_app.tasks.items():
        logger.info('name: %s, task: %s', complete_task_name, task)


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

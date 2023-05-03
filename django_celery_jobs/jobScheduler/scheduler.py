import six
import logging
from datetime import tzinfo
from pytz import timezone
from tzlocal import get_localzone

from .jobstore import JobStore
from .trigger.base import BaseTrigger
from .trigger.cron import CronTrigger
from .core.celery.utils import get_celery_app, autodiscover_tasks
from ..models import CeleryNativeTaskModel


class JobSchedulerHandler:
    JOBSTORE_CLASS = JobStore
    TRIGGER_CLASSES = {
        'cron': CronTrigger
    }

    def __init__(self, name=None, **options):
        self.name = name or __name__
        self.logger = logging.getLogger('job_scheduler')

        self.timezone = None
        self.configure(**options)

    def configure(self, **options):
        celery_app = get_celery_app()
        tz = celery_app.conf.timezone

        if not tz:
            tz = get_localzone()

        if isinstance(tz, six.string_types):
            tz = timezone(tz)

        if isinstance(tz, tzinfo):
            if tz.tzname(None) == 'local':
                raise ValueError('timezone name error (such as Europe/Helsinki)')

        self.timezone = tz

    def __getattr__(self, name):
        raise AttributeError

    @staticmethod
    def get_celery_native_tasks():
        tasks = []
        autodiscover_tasks()
        app = get_celery_app()

        for task_name, task in app.tasks.items():
            backend_cls = task.backend.__class__
            backend_mod = backend_cls.__module__
            backend_name = backend_cls.__name__

            item = dict(
                name='',
                task=task_name,
                backend=backend_mod + ":" + backend_name,
                priority=task.priority,
                ignore_result=task.ignore_result,
            )
            tasks.append(item)

        return tasks

    def get_jobs(self, job_ids=None):
        return self._lookup_jobstore().get_all_jobs(job_ids)

    def get_job(self, job_id):
        return self._lookup_jobstore(job_id=job_id).get_job()

    def add_job(self, **options):
        return self._lookup_jobstore(**options).add_job()

    def modify_job(self, job_id, **kwargs):
        return self._lookup_jobstore(job_id=job_id, **kwargs).update_job()

    def remove_job(self, job_id):
        return self._lookup_jobstore(job_id=job_id).remove_job()

    def _lookup_jobstore(self, **opts):
        trigger = opts.pop('trigger', 'cron')
        trigger = self._create_trigger(trigger, **opts)

        return self.JOBSTORE_CLASS(trigger=trigger, **opts)

    def _create_trigger(self, trigger=None, **options):
        if isinstance(trigger, BaseTrigger):
            return trigger
        elif trigger is None:
            trigger = 'cron'
        elif not isinstance(trigger, six.string_types):
            raise TypeError('Expected a trigger instance or string, got %s instead' % trigger.__class__.__name__)
        elif trigger not in self.TRIGGER_CLASSES:
            raise ValueError('Expected trigger: %s' % ', '.join(self.TRIGGER_CLASSES.keys()))

        options['timezone'] = self.timezone
        return self.TRIGGER_CLASSES[trigger](**options)


default_scheduler = JobSchedulerHandler()

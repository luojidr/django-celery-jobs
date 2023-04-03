import six
import json

from .util import get_celery_app


class Job(object):
    __slots__ = ('_scheduler', 'name', 'task', 'args', 'kwargs', 'queue', 'exchange',
                 'routing_key', 'expires', 'enabled', 'last_run_at', 'total_run_count',
                 'date_changed', 'description', 'crontab_id', 'interval_id', 'solar_id',
                 'one_off', 'start_time', 'priority', 'headers', 'clocked_id', 'expire_seconds')

    def __init__(self, scheduler, name=None, **kwargs):
        super(Job, self).__init__()
        self._scheduler = scheduler
        self._modify(name=name, **kwargs)

    def modify(self, **job_kwargs):
        self._scheduler.modify_job(self.name, **job_kwargs)
        return self

    def stop(self):
        self._scheduler.stop_job(self.name)
        return self

    def start(self):
        self._scheduler.resume_job(self.name)
        return self

    def remove(self):
        self._scheduler.remove_job(self.name)

    def get_next_run_time(self):
        pass

    def _modify(self, **job_kwargs):
        approved = {}
        celery_app = get_celery_app()

        task = job_kwargs.pop('task')
        if not isinstance(task, celery_app.Task) and not callable(task):
            raise TypeError('task must be a callable or a `celery.app.task:Task` instance')

        task = celery_app.task(task)
        name = job_kwargs.pop('name', task.name)

        priority = job_kwargs.pop('priority', None)
        if priority is not None and priority > 255:
            raise ValueError('priority maximum is 255.')

        trigger = job_kwargs.pop('trigger')
        clocked_id = trigger.id

        approved.update(
            name=name, task=task.name,
            args=json.dumps(job_kwargs.pop('args', None) or ()),
            kwargs=json.dumps(job_kwargs.pop('kwargs', None) or {}),
            headers=json.dumps(job_kwargs.pop('headers', None) or {}),
            enabled=False, priority=priority, clocked_id=clocked_id,
        )

        for attr in self.__slots__:
            approved[attr] = job_kwargs.pop(attr, None)

        if job_kwargs:
            raise AttributeError('The following are not modifiable attributes of Job: %s' % ', '.join(job_kwargs))

        for key, value in six.iteritems(approved):
            setattr(self, key, value)

    def __repr__(self):
        return 'Job<name:%s>' % self.name

    def __str__(self):
        datetime_repr = (lambda v: v.strftime('%Y-%m-%d %H:%M:%S') if v else 'None')

        if hasattr(self, 'next_run_time'):
            status = 'next run at: %s' % datetime_repr(self.next_run_time) if self.next_run_time else 'paused'
        else:
            status = 'pending'

        return 'Job<name:%s, trigger:%s, %s>' % (self.name, self.crontab_id, status)


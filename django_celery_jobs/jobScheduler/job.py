import six
import json


class Job(object):
    __slots__ = (
        '_scheduler', 'title', 'config_id', 'periodic_task_id', 'crontab_id',
        'is_enabled', 'args', 'kwargs', 'priority',  'max_run_cnt', 'deadline_run_time',
        'queue_name', 'exchange_name', 'routing_key',  'func_name', 'task_source_code',
    )

    def __init__(self, scheduler, name=None, **kwargs):
        super(Job, self).__init__()
        self._scheduler = scheduler
        self._modify(name=name, **kwargs)

    def modify(self, **job_kwargs):
        self._scheduler.modify_job(self.title, **job_kwargs)
        return self

    def stop(self):
        self._scheduler.stop_job(self.title)
        return self

    def start(self):
        self._scheduler.resume_job(self.title)
        return self

    def remove(self):
        self._scheduler.remove_job(self.title)

    def get_next_run_time(self):
        pass

    def _modify(self, **job_kwargs):
        approved = {
            'title': job_kwargs.pop('title'),
            'config_id': job_kwargs.pop('config_id'),
            'periodic_task_id': job_kwargs.pop('periodic_task_id', None),
            'args': json.loads(job_kwargs.pop('args', None) or ()),
            'kwargs': json.loads(job_kwargs.pop('kwargs', None) or {}),
            'exchange_name': job_kwargs.pop('exchange_name', None),
            'routing_key': job_kwargs.pop('routing_key', None),
            'is_enabled': False,
        }

        # crontab
        pass

        priority = job_kwargs.pop('priority', None)
        if priority is not None and priority > 255:
            raise ValueError('priority maximum is 255.')

        queue_name = job_kwargs.pop('queue_name', None)
        if not queue_name:
            raise ValueError('Queue name is not allowed empty.')

        namespace = {'__builtins__': {}}
        func_name = job_kwargs.pop('func_name', '')
        task_source_code = job_kwargs.pop('task_source_code', '')

        if task_source_code:
            exec(task_source_code, namespace)
            np_keys = [k for k in namespace.keys() if not k.startswith('_')]

            if func_name and func_name != np_keys[0]:
                raise ValueError("Function name do not match.")
            else:
                func_name = np_keys[0]

        approved.update(
            priority=priority, queue_name=queue_name,
            func_name=func_name, task_source_code=task_source_code,
        )

        for attr in job_kwargs:
            if attr not in self.__slots__:
                raise AttributeError('Job not include `%s` field: %s' % attr)

            approved[attr] = job_kwargs.pop(attr, '')

        for key, value in six.iteritems(approved):
            setattr(self, key, value)

    def __repr__(self):
        return 'Job<name:%s>' % self.title

    def __str__(self):
        datetime_repr = (lambda v: v.strftime('%Y-%m-%d %H:%M:%S') if v else 'None')

        if hasattr(self, 'next_run_time'):
            status = 'next run at: %s' % datetime_repr(self.next_run_time) if self.next_run_time else 'paused'
        else:
            status = 'pending'

        return 'Job<name:%s, trigger:%s, %s>' % (self.title, self.crontab_id, status)


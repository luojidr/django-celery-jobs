import json

from django.utils import timezone

from ..models import JobPeriodicModel
from .trigger.base import BaseTrigger


class Job:
    _task_slots = ('name', 'task', 'args', 'kwargs', 'queue', 'exchange', 'routing_key',
                   'expires', 'enabled', 'last_run_at', 'total_run_count', 'date_changed',
                   'description', 'crontab_id', 'interval_id', 'clocked_id', 'solar_id',
                   'priority', 'one_off', 'start_time', 'headers', 'expire_seconds')

    _job_slots = ('title', 'is_enabled', 'max_run_cnt', 'config_id', 'func_name',
                  'periodic_task_id', 'deadline_run_time', 'task_source_code', 'remark')

    def __init__(self, **options):
        self.job = self._get_cleaned_job(**options)
        self.beat_task = self._get_cleaned_task(**options)
        self.trigger = options.pop('trigger', None)

        if isinstance(self.trigger, BaseTrigger):
            raise ValueError('trigger must be instance of BaseTrigger')

    def _get_cleaned_job(self, **options):
        approved = {
            'is_enabled': False, 'periodic_task_id': None,
            'func_name': options.pop('func_name') or '',
            'deadline_run_time': None,
            'remark': options.pop('remark', ''),

        }

        title = options.pop("title", None)
        if not title:
            raise ValueError("Job title can not be empty and unique.")
        approved['title'] = title

        config_id = options.pop('config_id', None)
        if not config_id:
            raise ValueError('Job conf can not be empty')
        approved['config_id'] = config_id

        max_run_cnt = int(options.pop('max_run_cnt', 0))
        approved['max_run_cnt'] = max_run_cnt
        if max_run_cnt:
            deadline_run_time = self.trigger.get_last_run_time(max_run_cnt)
            approved.update(deadline_run_time=deadline_run_time.strftime("%Y-%m-%d %H:%M:%S"))

        namespace = {'__builtins__': {}}
        func_name = options.pop('func_name', '')
        task_source_code = options.pop('task_source_code', '')
        approved['task_source_code'] = task_source_code

        if task_source_code:
            exec(task_source_code, namespace)
            ns_keys = [k for k in namespace.keys() if not k.startswith('_')]
            approved['func_name'] = ns_keys[0]
        else:
            approved['func_name'] = func_name

        return approved

    def _get_cleaned_task(self, **options):
        approved = {
            'enabled': 0, 'last_run_at': None,
            'total_run_count': 0, 'date_changed': timezone.datetime.now(),
            'args': options.pop('args', None),
            'exchange': options.pop('exchange', None),
            'routing_key': options.pop('routing_key', None),
            'expires': options.pop('expires', None),
            'description': '', 'interval_id': None, 'clocked_id': None,
            'solar_id': None, 'priority': options.pop('priority', None),
            'one_off': 0, 'start_time': None, 'headers': '{}',
            'expire_seconds': None,
        }

        name = options.pop("name", None)
        if not name:
            raise ValueError("Job name can not be empty and unique.")
        approved['name'] = name

        try:
            args = json.dumps(json.loads(options.pop('args', '[]')))
            kwargs = json.dumps(json.loads(options.pop('kwargs', '{}')))
        except (json.JSONDecodeError, json.JSONEncoder):
            raise
        approved.update(args=args, kwargs=kwargs)

        trigger_schedule = self.trigger.get_trigger_schedule()
        approved.update(**trigger_schedule)

        return approved

    def get_next_run_time(self):
        return self.trigger.get_next_run_time()

    def get_all_jobs(self):
        pass

    def add_job(self, job):
        pass

    def update_job(self, job):
        pass

    def remove_job(self, name):
        pass

    def _lookup_job(self, name):
        pass

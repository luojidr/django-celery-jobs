import json
from copy import deepcopy
from collections import OrderedDict

from django.utils import timezone
from django.db import transaction, DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.models import PeriodicTask

from .trigger.base import BaseTrigger
from ..models import JobPeriodicModel

__all__ = ('JobStore', )


class JobStore:
    def __init__(self, **options):
        self.job_id = options.pop("job_id", None)
        self.trigger = options.pop('trigger', None)

        if isinstance(self.trigger, BaseTrigger):
            raise ValueError("trigger must be instance of BaseTrigger's subclass")

        self._options = deepcopy(options)

    @property
    def job(self):
        instance = getattr(self, "_job_instance", None)

        if not instance and self.job_id:
            instance = self._lookup_job(self.job_id)
            setattr(self, "_job_instance", instance)

        return instance

    def _init_model_default(self, model_or_object):
        opts = {}

        for field in model_or_object._meta.fields:
            field_name = field.name

            if not field.primary_key:
                # many_to_many: ManyToManyField
                #  many_to_one: ForeignKey
                #  one_to_many: GenericRelation, the reverse of a ForeignKey
                #   one_to_one: OneToOneField
                if any([field.many_to_many, field.many_to_one, field.one_to_many, field.one_to_one]):
                    field_name = field.name + '_id'

                opts[field_name] = field.get_default()

        return opts

    def _get_job_opts(self, **options):
        approved = self._init_model_default(model_or_object=JobPeriodicModel)
        approved.update(
            remark=options.pop('remark', approved['remark']),
            func_name=options.pop('func_name', approved['func_name']),
        )

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

    def _get_beat_task_opts(self, **options):
        approved = self._init_model_default(model_or_object=PeriodicTask)
        approved.update(
            priority=options.pop('priority', approved['priority']),
            exchange=options.pop('exchange', approved['exchange']),
            routing_key=options.pop('routing_key', approved['routing_key']),
            expires=options.pop('expires', approved['expires']),
        )

        name = options.pop("name", None)
        if not name:
            raise ValueError("Job name can not be empty and unique.")
        approved['name'] = name

        try:
            args = json.dumps(json.loads(options.pop('args', approved['args'])))
            kwargs = json.dumps(json.loads(options.pop('kwargs', approved['kwargs'])))
        except (json.JSONDecodeError, json.JSONEncoder):
            raise
        approved.update(args=args, kwargs=kwargs)

        trigger_schedule = self.trigger.get_trigger_schedule()
        approved.update(**trigger_schedule)

        return approved

    def get_next_run_time(self):
        return self.trigger.get_next_run_time()

    def get_all_jobs(self, job_ids=None):
        return self._lookup_job(job_ids)

    def get_job(self):
        return self._lookup_job(self.job_id)

    def add_job(self):
        with transaction.atomic():
            sid = transaction.savepoint()  # 开启事务设置事务保存点

            try:
                beat_task_opts = self._get_beat_task_opts(**self._options)
                periodic_task = PeriodicTask.objects.create(**beat_task_opts)

                job_opts = self._get_job_opts(**self._options)
                job_opts['periodic_task_id'] = periodic_task.id
                instance = JobPeriodicModel.objects.create(**job_opts)
                self.job_id = instance.id

                return self.job
            except:
                transaction.savepoint_rollback(sid)
                raise DatabaseError('Jobstore to save job failed.')
            finally:
                transaction.savepoint_commit(sid)

    def update_job(self):
        model_opts = OrderedDict()
        beat_task = self.job.periodic_task if self.job else None

        with transaction.atomic():
            if beat_task:
                model_opts[beat_task] = self._get_beat_task_opts(**self._options)

            if self.job:
                model_opts[self.job] = self._get_job_opts(**self._options)

            for orm_object, approved_opts in model_opts.items():
                for name, new_value in approved_opts.items():
                    db_value = getattr(orm_object, name)

                    if new_value and db_value != new_value:
                        setattr(orm_object, name, new_value)
                else:
                    orm_object.save()

        return self.job

    def remove_job(self):
        assert self.job, ObjectDoesNotExist("JobPeriodicModel<id:%s> not exist" % self.job_id)

        with transaction.atomic():
            beat_task = self.job.periodic_task
            beat_task.enabled = False
            self.job.is_del = True
            self.job.is_enabled = False

            beat_task.save()
            self.job.save()

    def _lookup_job(self, job_ids=None):
        q = dict(
            periodic_task_id__gt=0,
            is_enabled=True, is_del=False
        )
        queryset = JobPeriodicModel.objects.filter(**q).all()

        if job_ids is None:  # All jobs
            return queryset

        if isinstance(job_ids, (list, tuple)):
            return queryset.filetr(id__in=job_ids)

        assert isinstance(job_ids, int), ValueError('Parameter `job_ids` type not allowed')
        return queryset.filter(id=job_ids).first()

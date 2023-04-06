import re
import logging
import platform
import traceback
from urllib.parse import quote_plus

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator

from celery import states
from celery.utils.nodenames import default_nodename
from django_celery_beat.models import PeriodicTask, CrontabSchedule, CrontabSchedule
from django_celery_results.models import TaskResult, TASK_STATE_CHOICES

from .jobScheduler.util import get_ip_addr

UserModel = get_user_model()
DEFAULT_TIME = "1979-01-01 00:00:00"


class BaseAbstractModel(models.Model):
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    is_del = models.BooleanField(verbose_name='是否删除', default=False)

    class Meta:
        abstract = True

    @classmethod
    def fields(cls):
        # cls._meta.concrete_fields
        abc_fields = [_field.name for _field in BaseAbstractModel._meta.fields]
        return [f.name for f in cls._meta.fields if f.name not in abc_fields]

    @classmethod
    def create_object(cls, **kwargs):
        """ create object """
        fields = cls.fields()
        new_kwargs = {key: value for key, value in kwargs.items() if key in fields}

        return cls.objects.create(**new_kwargs)

    def save_attrs(self, **attrs):
        fields = self.fields()
        cleaned_attrs = {name: value for name, value in attrs.items() if name in fields}

        for name, value in cleaned_attrs.items():
            setattr(self, name, value)

        cleaned_attrs and self.save()

    @classmethod
    def add_result(cls, **kwargs):
        try:
            return cls.create_object(
                **dict(
                    system=platform.system(), node=default_nodename(None),
                    ip_address=get_ip_addr(), **kwargs
                )
            )
        except Exception:
            logging.error(traceback.format_exc())


class JobConfigModel(BaseAbstractModel):
    CATEGORY_CHOICES = [
        (1, 'broker'),  # Celery Broker
        (2, 'ssh'),     # Local or Remote to execute command
        (3, 'http'),    # Http Request to api
    ]
    AS_URI = {
        'broker': '{transport}://{user}:{password}@{host}:{port}/{virtual_host}',
        'http:': '{transport}://{host}/'
    }

    owner = models.ForeignKey(to=UserModel, default=None, null=True, on_delete=models.SET_NULL)
    transport = models.CharField("Transport", max_length=50, default='', blank=True)
    user = models.CharField("User", max_length=50, default='', blank=True)
    pwd = models.CharField("Password", max_length=200, default='', blank=True)
    host = models.CharField("Host", max_length=50, default='', blank=True)
    port = models.IntegerField("Port", default=0, blank=True)
    virtual = models.CharField("Broker Virtual Host", max_length=50, default='', blank=True)

    # 公私钥 | http

    category = models.SmallIntegerField("Config Category", choices=CATEGORY_CHOICES, default=0, blank=True)

    class Meta:
        db_table = 'django_celery_jobs_config'
        ordering = ["-id"]

    def as_url(self):
        uri_kwargs = dict(
            transport=self.transport,
            user=self.user, password=self.pwd,
            host=self.host, port=self.port,
            virtual_host=quote_plus(self.virtual),
        )

        if self.category == 1:
            as_uri = '{transport}://{user}:{password}@{host}:{port}/{virtual_host}'
        else:
            raise ValueError("Not Implement.")

        return as_uri.format(**uri_kwargs)


class PeriodicJobModel(BaseAbstractModel):
    title = models.CharField("Task Title", unique=True, max_length=500, default='')
    config = models.ForeignKey(to=JobConfigModel, related_name="config",
                               default=None, null=True, on_delete=models.SET_NULL)
    periodic_task = models.ForeignKey(to=PeriodicTask, related_name="periodic_task",
                                      default=None, null=True, on_delete=models.SET_NULL)
    crontab = models.ForeignKey(to=CrontabSchedule, related_name="crontab",
                                default=None, null=True, on_delete=models.SET_NULL)
    is_enabled = models.BooleanField("Start or not", default=False, blank=True)
    args = models.JSONField('Positional Arguments', blank=True, default=list)
    kwargs = models.JSONField('Keyword Arguments', blank=True, default=dict)
    priority = models.PositiveIntegerField(
        'Priority', validators=[MaxValueValidator(255)], default=None, blank=True,
        null=True, help_text='Priority Number between 0 and 255, (priority reversed, 0 is highest)'
    )
    max_run_cnt = models.IntegerField("Maximum execution times", default=0, blank=True)
    deadline_run_time = models.DateTimeField('Deadline run datetime', blank=True, null=True, default=None)
    queue_name = models.CharField("Queue Name", max_length=200, default='')
    exchange_name = models.CharField("Exchange Name", max_length=200, default='')
    routing_key = models.CharField("Route Key", max_length=200, default='')
    func_name = models.CharField("Func Name", max_length=100, default='')
    task_source_code = models.CharField("Task Source Code", max_length=5000, default='')

    # SSH 执行脚本(本地或远程, 一种定时任务的实现) paramiko
    # directory = models.CharField("Directory where the command is executed", max_length=1000, default='')
    # command = models.CharField("Script execution command", max_length=1000, default='')

    remark = models.CharField("remark", max_length=1000, default='')

    class Meta:
        db_table = 'django_celery_jobs_periodic_task'
        ordering = ["-id"]

    @classmethod
    def get_enabled_tasks(cls):
        return cls.objects.filter(is_enabled=True).all()

    def compile_task_func(self):
        if not self.task_source_code:
            return

        func_obj = None
        namespace = {'__builtins__': {}}
        func_source_code = self.task_source_code.strip()
        exec(func_source_code, namespace)

        for name, obj in namespace.items():
            if callable(obj) and getattr(obj, "__name__", None) == name:
                func_obj = obj
                break

        assert func_obj, "PeriodicJobModel<id:%s> hasn't source code" % self.id
        return func_obj


class CeleryPeriodicJobModel(PeriodicTask):
    """ django_celery_beat.models:PeriodicTask """
    class Meta:
        proxy = True


class JobScheduledResultModel(BaseAbstractModel):
    sched_id = models.CharField(verbose_name="Scheduled Id", max_length=100, default="", db_index=True, blank=True)
    name = models.CharField(verbose_name="Scheduled Name", max_length=300, default="", blank=True)
    periodic_task_id = models.IntegerField(verbose_name="Periodic Task Id", default=0, blank=True)
    run_date = models.DateTimeField(verbose_name="Run Datetime", default=DEFAULT_TIME, blank=True)
    is_success = models.BooleanField(verbose_name="Is Success", default=False, blank=True)
    system = models.CharField(verbose_name="System", max_length=100, default="", blank=True)
    ip_address = models.CharField(verbose_name="Ip", max_length=20, default="", blank=True)
    node = models.CharField(verbose_name="Node", max_length=100, default="", blank=True)
    traceback = models.CharField(verbose_name="Traceback", max_length=3000, default="", blank=True)
    remark = models.CharField("Remark", max_length=300, default='', blank=True)

    class Meta:
        db_table = 'django_celery_jobs_scheduled_result'
        ordering = ["-id"]

    @classmethod
    def update_scheduled_result(cls, sched_id, **attrs):
        sched_obj = cls.objects.filter(sched_id=sched_id).first()

        if not sched_obj:
            return

        sched_obj.save_attrs(**attrs)


class JobRunnerResultModel(BaseAbstractModel):
    """ Extra Jobs to Store DB """
    task_id = models.CharField("Job ID", max_length=100, default='', blank=True)
    task_name = models.CharField("Job Name", max_length=200, default='', blank=True)
    periodic_task_id = models.IntegerField("Periodic Task Id", default=0, blank=True)
    status = models.CharField("Job Status", max_length=50,
                              default=states.PENDING, choices=TASK_STATE_CHOICES, blank=True)
    cost_seconds = models.IntegerField("Cost Seconds", default=0, blank=True)
    args = models.JSONField('Positional Arguments', blank=True, default=list)
    kwargs = models.JSONField('Keyword Arguments', blank=True, default=dict)
    result = models.CharField('Job Result', max_length=2000, default='', blank=True)
    run_date = models.DateTimeField(verbose_name="Run Datetime", default=DEFAULT_TIME, blank=True)
    traceback = models.CharField(verbose_name="Traceback", max_length=3000, default="", blank=True)
    done_date = models.DateTimeField(verbose_name="Done Datetime", default=DEFAULT_TIME, blank=True)
    system = models.CharField(verbose_name="System", max_length=100, default="", blank=True)
    ip_address = models.CharField(verbose_name="Ip", max_length=20, default="", blank=True)
    node = models.CharField(verbose_name="Node", max_length=100, default="", blank=True)
    remark = models.CharField("remark", max_length=300, default='', blank=True)

    class Meta:
        db_table = 'django_celery_jobs_runner_result'
        ordering = ["-id"]


class CeleryJobRunnerResultModel(TaskResult):
    """ django_celery_results.models:TaskResult """
    class Meta:
        proxy = True

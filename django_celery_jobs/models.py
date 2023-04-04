import logging
import platform
import traceback
from urllib.parse import quote_plus

from django.db import models
from django.contrib.auth import get_user_model

from celery import states
from celery.schedules import crontab
from celery.utils.nodenames import default_nodename
from django_celery_beat.models import PeriodicTask, CrontabSchedule
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
        return [f.name for f in cls._meta.concrete_fields]

    @classmethod
    def create_object(cls, **kwargs):
        """ create object """
        fields = cls.fields()
        new_kwargs = {key: value for key, value in kwargs.items() if key in fields}

        return cls.objects.create(**new_kwargs)

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


class BrokerConfigModel(BaseAbstractModel):
    user = models.ForeignKey(to=UserModel, default=None, null=True, on_delete=models.SET_NULL)
    transport = models.CharField(verbose_name="Transport", max_length=50, default='', blank=True)
    broker_user = models.CharField(verbose_name="Broker User", max_length=50, default='', blank=True)
    broker_pwd = models.CharField(verbose_name="Broker Password", max_length=200, default='', blank=True)
    broker_host = models.CharField(verbose_name="Broker Host", max_length=50, default='', blank=True)
    broker_port = models.IntegerField(verbose_name="Broker Port", default=0, blank=True)
    broker_virtual = models.CharField(verbose_name="Broker Virtual Host", max_length=50, default='')

    class Meta:
        db_table = 'django_celery_jobs_broker_config'
        ordering = ["-id"]

    def get_broker_url(self):
        """ {transport}://{user}:{password}@{host}:{port}/{virtual_host}
        eg: amqp://admin:adminp@127.0.0.1:5672/%2Ftest
        """
        broker_kwargs = dict(
            transport=self.transport,
            user=self.broker_user, password=self.broker_pwd,
            host=self.broker_host, port=self.broker_port,
            virtual_host=quote_plus(self.broker_virtual),
        )
        broker_fmt = "{transport}://{user}:{password}@{host}:{port}/{virtual_host}"
        broker_url = broker_fmt.format(**broker_kwargs)

        return broker_url


class PeriodicJobModel(BaseAbstractModel):
    title = models.CharField("Task Title", max_length=500, default='')
    broker = models.ForeignKey(to=BrokerConfigModel, related_name="broker",
                               default=None, null=True, on_delete=models.SET_NULL)
    periodic_task = models.ForeignKey(to=PeriodicTask, related_name="periodic_task",
                                      default=None, null=True, on_delete=models.SET_NULL)
    enabled = models.BooleanField("Start or not", default=False, blank=True)
    queue_name = models.CharField("Queue Name", max_length=200, default='')
    exchange_name = models.CharField("Exchange Name", max_length=200, default='')
    routing_key = models.CharField("Route Key", max_length=200, default='')
    func_name = models.CharField("Func Name", max_length=100, default='')
    task_source_code = models.CharField("Task Source Code", max_length=5000, default='')
    remark = models.CharField("remark", max_length=1000, default='')

    class Meta:
        db_table = 'django_celery_jobs_periodic_task'
        ordering = ["-id"]

    @classmethod
    def get_enabled_tasks(cls):
        return cls.objects.filter(enabled=True).all()

    def compile_task_func(self):
        if not self.task_source_code:
            return

        namespace = {}
        exec(self.task_source_code.strip(), namespace)
        func = namespace.get(self.func_name)

        assert func, "Periodic Job<fun:%s> has'nt source code" % self.func_name
        return func

    def get_crontab(self):
        cron_obj = CrontabSchedule.objects.get(id=self.periodic_task.crontab.id)
        return crontab(
            minute=cron_obj.minute, hour=cron_obj.hour, day_of_week=cron_obj.day_of_week,
            day_of_month=cron_obj.day_of_month, month_of_year=cron_obj.month_of_year
        )


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
        fields = cls.fields()
        sched_obj = cls.objects.filter(sched_id=sched_id).first()

        if not sched_obj:
            return

        for name, value in attrs.items():
            if name in fields:
                setattr(sched_obj, name, value)

        sched_obj.save()


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

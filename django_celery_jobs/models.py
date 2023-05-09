import json
import logging
import platform
import traceback
from itertools import chain
from urllib.parse import quote_plus

from django.utils import timezone
from django.db import models, transaction
from django.contrib.auth import get_user_model

from celery import states
from celery.utils.nodenames import default_nodename
from django_celery_beat.models import PeriodicTask, cronexp
from django_celery_results.models import TaskResult, TASK_STATE_CHOICES

from .jobScheduler.utils import get_ip_addr
from .jobScheduler.trigger.cron import CronTrigger
from .jobScheduler.core.enums.deploy import DeployModeEnum
from .jobScheduler.core.exceptions import DeployModeError

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


class JobPeriodicModel(BaseAbstractModel):
    title = models.CharField("Task Title", unique=True, max_length=255, default='', blank=True)
    config = models.ForeignKey(to=JobConfigModel, related_name="config",
                               default=None, null=True, on_delete=models.SET_NULL)
    periodic_task = models.ForeignKey(to=PeriodicTask, related_name="periodic_task",
                                      default=None, null=True, on_delete=models.SET_NULL)
    is_enabled = models.BooleanField("Start or not", default=False, blank=True)
    max_run_cnt = models.IntegerField("Maximum execution times", default=0, blank=True)
    first_run_time = models.DateTimeField('First run datetime', blank=True, null=True, default=None)
    deadline_run_time = models.DateTimeField('Deadline run datetime', blank=True, null=True, default=None)
    func_name = models.CharField("Func Name", max_length=100, default='', blank=True)
    task_source_code = models.TextField("Task Source Code", default='', blank=True)

    # SSH 执行脚本(本地或远程, 一种定时任务的实现) paramiko
    # directory = models.CharField("Execution directory", max_length=1000, default='', blank=True)
    # command = models.TextField("Script Execution command", default='', blank=True)

    remark = models.CharField("remark", max_length=1000, default='')

    class Meta:
        db_table = 'django_celery_jobs_periodic_task'
        ordering = ["-id"]

    @classmethod
    def perform_save(cls, serializer):
        """ Create or Update to save """
        from django_celery_jobs.views import CronExpressionApi

        job_id = int(serializer.initial_data.get('id') or 0)
        cron_expr = serializer.initial_data['cron_expr']
        max_run_cnt = serializer.validated_data.get('max_run_cnt', 0)

        trigger = CronTrigger.from_crontab(expr=cron_expr)
        crontab_id = trigger.get_trigger_schedule()['crontab_id']

        # Other kwargs to create or update
        kwargs = {}
        if max_run_cnt:
            run_next_time_list = CronExpressionApi.get_run_next_time_list(cron_expr, max_run_cnt)
            kwargs['deadline_run_time'] = timezone.datetime.strptime(run_next_time_list[-1], "%Y-%m-%d %H:%M:%S")

        if not job_id:
            # create periodic task
            native_job_id = serializer.initial_data['native_job_id']
            native_job = CeleryNativeTaskModel.objects.get(id=native_job_id)

            beat_name = native_job.task
            beat_periodic_task_obj = BeatPeriodicTaskModel(
                task=beat_name,
                name=beat_name.rsplit('.', 1)[-1] + timezone.datetime.now().strftime("_%Y%m%d%H%M%S_%f"),
            )
            kwargs['first_run_time'] = timezone.datetime.now()

        else:
            # update periodic task
            beat_periodic_task_obj = serializer.instance.periodic_task

        with transaction.atomic():
            job_obj = serializer.save(**kwargs)

            beat_periodic_task_obj.crontab_id = crontab_id
            beat_periodic_task_obj.enabled = job_obj.is_enabled
            beat_periodic_task_obj.kwargs = json.dumps(dict(job_id=job_obj.id))
            beat_periodic_task_obj.save()

            job_obj.periodic_task_id = beat_periodic_task_obj.id
            job_obj.save()

    def compile_task_func(self):
        if not self.task_source_code:
            return

        namespace = {'__builtins__': {}}
        func_source_code = self.task_source_code.strip()
        exec(func_source_code, namespace)
        func = namespace.get(self.func_name)

        assert func, "PeriodicJobModel<id:%s>'s `func_name` does not exist" % self.id
        return func

    @property
    def cron_expr(self):
        crontab = self.periodic_task.crontab
        return '{} {} {} {} {}'.format(
            cronexp(crontab.minute), cronexp(crontab.hour), cronexp(crontab.day_of_month),
            cronexp(crontab.month_of_year), cronexp(crontab.day_of_week)
        )

    @property
    def native_task_name(self):
        native_obj = CeleryNativeTaskModel.objects.filter(task=self.periodic_task.task, is_del=False).first()
        return native_obj.name if native_obj else ''


class CeleryNativeTaskModel(BaseAbstractModel):
    name = models.CharField("Name", max_length=500, default='', blank=True)
    task = models.CharField("Task", max_length=500, unique=True, default='', blank=True)
    backend = models.CharField("Backend", max_length=500, default='', blank=True)
    priority = models.IntegerField("Priority", null=True, default=None, blank=True)
    ignore_result = models.BooleanField("Ignore Result", default=False, blank=True)
    is_hidden = models.BooleanField("Hidden", default=False, blank=True)
    desc = models.CharField("Desc", max_length=500, default='', blank=True)

    class Meta:
        db_table = 'django_celery_jobs_native_jobs'
        ordering = ["-id"]

    @classmethod
    def create_or_update_native_task(cls, **kwargs):
        task = kwargs.get('task')
        if task:
            kwargs['is_hidden'] = task.startswith('celery.')

        native_task = cls.objects.filter(task=task).first()
        if native_task:
            return native_task.save_attrs(**kwargs)

        return cls.create_object(**kwargs)


class BeatPeriodicTaskModel(PeriodicTask):
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


class CeleryTaskRunnerResultModel(TaskResult):
    """ django_celery_results.models:TaskResult """
    class Meta:
        proxy = True


class DeployOptionModel(BaseAbstractModel):
    MODE_CHOICES = DeployModeEnum.members()

    # 1,2,5 比较常见的部署方式, 3, 4细细研究
    mode = models.SmallIntegerField("Deploy Mode", choices=MODE_CHOICES, default=1, blank=True)
    name = models.CharField("Name", max_length=30, default='', blank=True)
    alias = models.CharField("Alias", max_length=100, default='', blank=True)
    value = models.CharField("Value", max_length=5000, default='', blank=True)
    order = models.IntegerField("Order", default=1, blank=True)
    description = models.CharField("Description", max_length=500, default='', blank=True)

    class Meta:
        db_table = 'django_celery_jobs_deploy_options'
        ordering = ['order']

    @classmethod
    def get_options_by_mode(cls, mode):
        """
        :param mode int|str, name or enum.name of DeployModeEnum
        """
        valid_modes = [(_enum.name.lower(), _enum.mode) for _enum in DeployModeEnum.iterator()]

        if mode not in list(chain.from_iterable(valid_modes)):
            raise DeployModeError("mode: %s is invalid." % mode)

        mode_map = dict(valid_modes)
        mode = mode_map.get(mode, mode)

        return cls.objects.filter(mode=mode, is_del=False).all()


class DeployLogMode(BaseAbstractModel):
    user_id = models.IntegerField("UserId", default=0, blank=True)
    deploy_id = models.IntegerField("DeployId", default=0, blank=True)

    class Meta:
        db_table = 'django_celery_jobs_deploy_log'
        abstract = True


class AlarmTemplateModel(BaseAbstractModel):
    """ Alarm template to notify """
    name = models.CharField("Alarm Name", max_length=100, default='', blank=True)

    class Meta:
        abstract = True

import logging
import platform
import traceback

from django.db import models
from django.utils import timezone
from django_celery_beat.models import PeriodicTask


class BaseAbstractModel(models.Model):
    DEFAULT_TIME = "1979-01-01 00:00:00"

    creator = models.CharField(verbose_name="创建人", max_length=200, default='')
    modifier = models.CharField(verbose_name="创建人", max_length=200, default='')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    is_del = models.BooleanField(verbose_name='是否删除', default=False)
    run_time_at = models.DateTimeField(verbose_name="运行时间", default=DEFAULT_TIME, blank=True)
    is_success = models.BooleanField(verbose_name="是否成功", default=False, blank=True)
    system = models.CharField(verbose_name="平台", max_length=100, default="", blank=True)
    node = models.CharField(verbose_name="主机节点", max_length=100, default="", blank=True)
    exc_info = models.CharField(verbose_name="运行异常", max_length=2000, default="", blank=True)
    remark = models.CharField("remark", max_length=300, default='', blank=True)

    class Meta:
        abstract = True

    @classmethod
    def create_object(cls, **kwargs):
        """ create object """
        fields = [f.name for f in cls._meta.concrete_fields]
        new_kwargs = {key: value for key, value in kwargs.items() if key in fields}
        new_kwargs.update(
            run_time_at=timezone.now(),
            system=platform.system(), node=platform.node(),
        )

        return cls.objects.create(**new_kwargs)


class JobScheduledRecord(BaseAbstractModel):
    name = models.CharField(verbose_name="Job调度名", max_length=300, default="", db_index=True, blank=True)
    periodic_task_id = models.IntegerField(verbose_name="定时任务ID", default=0, blank=True)

    class Meta:
        db_table = 'django_celery_jobs_scheduled_log'
        ordering = ["-id"]

    @classmethod
    def scheduled_log(cls, **kwargs):
        try:
            new_kwargs = dict(
                name=kwargs.get('name', ''),
                periodic_task_id=kwargs.get('periodic_task_id', 0),
                is_success=kwargs.get('is_success', False),
                exc_info=kwargs.get('exc_info', ''),
            )
            return cls.create_object(**new_kwargs)
        except Exception:
            logging.error(traceback.format_exc())


class JonRunnerRecord(BaseAbstractModel):
    name = models.CharField(verbose_name="Job运行名", max_length=300, default="", db_index=True, blank=True)
    cost_seconds = models.IntegerField(verbose_name="运行时间", default=0, blank=True)
    args = models.JSONField(verbose_name='Positional Arguments', blank=True, default='[]')
    kwargs = models.JSONField(verbose_name='Keyword Arguments', blank=True, default='{}')

    class Meta:
        db_table = 'django_celery_jobs_runner_log'
        ordering = ["-id"]
        abstract = True

    @classmethod
    def runner_log(cls, **kwargs):
        try:
            pass
        except Exception as e:
            logging.error(traceback.format_exc())

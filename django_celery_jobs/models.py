from django.db import models


class JobScheduledRecord(models.Model):
    DEFAULT_TIME = "1979-01-01 00:00:00"

    name = models.CharField(verbose_name="任务名", max_length=300, default="", db_index=True, blank=True)
    run_time = models.DateTimeField(verbose_name="撤回时间", default=DEFAULT_TIME, blank=True)
    is_success = models.BooleanField(verbose_name="调度是否成功", default=False, blank=True)
    traceback = models.CharField(verbose_name="调度异常", max_length=2000, default="", blank=True)

    class Meta:
        db_table = 'django_celery_jobs_scheduled_log'
        ordering = ["-id"]

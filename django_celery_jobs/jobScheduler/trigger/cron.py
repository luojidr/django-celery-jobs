import six
from collections import OrderedDict
from croniter import croniter

from django.conf import settings
from django.utils import timezone as tzinfo
from django_celery_beat.models import CrontabSchedule

from .base import BaseTrigger

__all__ = ['CronTrigger']


class CronTrigger(BaseTrigger):
    """ Specified time constraints, similarly to how the UNIX cron scheduler works

    :param int|str minute: minute (0-59) or * (Per minute)
    :param int|str hour: hour (0-23) or * (Per hour)
    :param int|str day_of_week: number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun) or * (Per week)
    :param int|str day_of_month: number of day (1-31) or *  (Per day)
    :param int|str month_of_year: number of month (1-12) or *  (Per month)
    :param datetime.tzinfo|str timezone: time zone to use for the date/time calculations (defaults
        to scheduler timezone)
    """
    ORDERED_FIELDS = ('minute', 'hour', 'day_of_month', 'month_of_year', 'day_of_week')
    __slots__ = ORDERED_FIELDS + ('expression', 'timezone')

    def __init__(self, minute=None, hour=None, day_of_month=None, month_of_year=None,
                 day_of_week=None, timezone=None, **kwargs):
        self.timezone = timezone or settings.TIME_ZONE
        self._crons = OrderedDict.fromkeys(self.ORDERED_FIELDS)

        for (key, value) in six.iteritems(locals()):
            if key in self.ORDERED_FIELDS:
                value = str(value) if value is not None else '*'
                self._crons[key] = value
                setattr(self, key, value)

        self.expression = " ".join([self._crons[k] for k in self._crons])

    @classmethod
    def from_crontab(cls, expr, timezone=None):
        """ Create a :class:`~CronTrigger` from a standard crontab expression """
        values = expr.split()
        if len(values) != 5:
            raise ValueError('Wrong number of fields; got {}, expected 5'.format(len(values)))

        return cls(minute=values[0], hour=values[1], day_of_month=values[2],
                   month_of_year=values[3], day_of_week=values[4], timezone=timezone)

    def get_next_run_time(self, now=None):
        cron = croniter(self.expression, now or tzinfo.datetime.now())
        return cron.get_next(tzinfo.datetime)

    def get_last_run_time(self, max_times, now=None):
        last_run_time = None
        cron = croniter(self.expression, now or tzinfo.datetime.now())

        for _ in range(max_times):
            last_run_time = cron.get_next(tzinfo.datetime)

        return last_run_time

    def get_next_time_range(self, max_times=None, now=None, fmt=False):
        next_time_list = []
        cron = croniter(self.expression, now or tzinfo.datetime.now())

        for i in range(max_times or self.max_times):
            next_run_time = cron.get_next(tzinfo.datetime)

            if fmt:
                next_time_list.append(next_run_time.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                next_time_list.append(next_run_time)

        return next_time_list

    def get_trigger_schedule(self):
        obj, created = CrontabSchedule.objects.get_or_create(**self._crons, timezone=self.timezone)
        return dict(crontab_id=obj.id)

    def __str__(self):
        return '<%s>: %s' % (self.timezone, self.expression)


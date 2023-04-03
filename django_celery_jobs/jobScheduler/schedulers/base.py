import os
import six
from logging import getLogger
from abc import ABCMeta, abstractmethod
from datetime import date, datetime, time, timedelta, tzinfo
from pytz import timezone
from tzlocal import get_localzone


# 解决多个scheduler(Celery beat)启动后的不会导致多个job重复执行和资源竞争的问题
class BaseScheduler(six.with_metaclass(ABCMeta)):
    # scheduler's stopped
    STATE_STOPPED = 0
    # scheduler's running: started and processing jobs
    STATE_RUNNING = 1
    # scheduler's paused: started but not processing jobs
    STATE_PAUSED = 2

    def __init__(self, name=None, **options):
        super(BaseScheduler, self).__init__()

        self.name = name or __name__
        self.state = self.STATE_STOPPED

        self.configure(**options)

    def configure(self, **options):
        self._logger = getLogger(self.name)
        tz = options.pop('timezone', None) or get_localzone()

        if isinstance(tz, six.string_types):
            tz = timezone(tz)
        if isinstance(tz, tzinfo):
            if tz.tzname(None) == 'local':
                raise ValueError('timezone name error (such as Europe/Helsinki)')
        self.timezone = tz

    def start(self, paused=False):
        """ Start celery beat command """
        if self.state != self.STATE_STOPPED:
            raise AlreadyRunningError("Scheduler<%s> is already running!" % self.name)

        self.state = self.STATE_PAUSED if paused else self.STATE_RUNNING
        self._logger.info('Scheduler<%s> started now' % self.name)

        if not paused:
            self.wakeup()

    @abstractmethod
    def shutdown(self, wait=True):
        pass

    @property
    def running(self):
        return self.state != self.STATE_STOPPED

    def add_job(self, **options):
        pass

    def get_jobs(self):
        pass

    def get_job(self):
        pass

    def modify_job(self, job_name):
        pass

    def start_job(self, job_name):
        pass

    def stop_job(self, job_name):
        pass

    def remove_job(self):
        pass

    def _lookup_job(self, job_id):
        pass

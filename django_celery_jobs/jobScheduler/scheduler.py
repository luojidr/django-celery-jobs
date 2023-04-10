import six
import logging
from datetime import tzinfo
from pytz import timezone
from tzlocal import get_localzone

from django.conf import settings

from .trigger.cron import CronTrigger
from .core.exceptions import AlreadyRunningError


class JobScheduler:
    TRIGGER_CLASSES = {
        'cron': CronTrigger
    }

    def __init__(self, name=None, **options):
        self.name = name or __name__
        self.logger = logging.getLogger('job_scheduler')

        self.timezone = None
        self.configure(**options)

    def configure(self, **options):
        tz = options.pop('timezone', None) or settings.TIME_ZONE or get_localzone()

        if isinstance(tz, six.string_types):
            tz = timezone(tz)

        if isinstance(tz, tzinfo):
            if tz.tzname(None) == 'local':
                raise ValueError('timezone name error (such as Europe/Helsinki)')

        self.timezone = tz

    def get_jobs(self):
        pass

    def get_job(self):
        pass

    def add_job(self, **options):
        pass

    def modify_job(self, job_name):
        pass

    def remove_job(self):
        pass

    def start_job(self, job_name):
        pass

    def stop_job(self, job_name):
        pass

    def _lookup_job(self, job_id):
        pass

    def _create_trigger(self, trigger, **options):
        return self.TRIGGER_CLASSES[trigger](**options)



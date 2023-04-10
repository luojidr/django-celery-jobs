
from .base import BaseTrigger


class IntervalTrigger(BaseTrigger):
    FIELDS = ('every', 'period')  # day, hour, minute, second

    def get_next_run_time(self, now=None):
        pass

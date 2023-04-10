
from .base import BaseTrigger


class ClockedTrigger(BaseTrigger):
    FIELDS = ('clocked_time',)

    def get_next_run_time(self, now=None):
        pass

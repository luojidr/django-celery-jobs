from threading import Event
from itertools import chain

from .base import BaseScheduler
from ..exceptions import CeleryAppError, AlreadyRunningError, NotRunningError


class BlockingScheduler(BaseScheduler):
    """ A scheduler that runs locally in the foreground """
    _event = None

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)

    def shutdown(self, wait=True):
        pass



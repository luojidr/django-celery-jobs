from threading import Event

from .base import BaseScheduler
from ..core.celery.bin import BeatService
from ..exceptions import CeleryAppError, AlreadyRunningError, NotRunningError


class CeleryJobScheduler(BaseScheduler):
    """ A scheduler that runs locally in the foreground """
    _event = None

    def start(self, *args, **kwargs):
        beat = BeatService(scheduler=self)
        beat.start()

    def shutdown(self, wait=True):
        pass


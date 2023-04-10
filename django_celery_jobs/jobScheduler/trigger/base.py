import six
from abc import ABCMeta, abstractmethod


class BaseTrigger(six.with_metaclass(ABCMeta)):
    @abstractmethod
    def get_next_run_time(self, now=None):
        """ Returns the next datetime  """

    @abstractmethod
    def get_trigger_schedule(self):
        pass

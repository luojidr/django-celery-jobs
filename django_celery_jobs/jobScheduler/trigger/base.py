import six
from abc import ABCMeta, abstractmethod


class BaseTrigger(six.with_metaclass(ABCMeta)):
    max_times = 10

    @abstractmethod
    def get_next_run_time(self, now=None):
        """ Returns the next datetime  """

    @abstractmethod
    def get_last_run_time(self, max_times, now=None):
        """ Returns the deadline datetime """

    @abstractmethod
    def get_next_time_range(self, max_times=None, now=None, fmt=False):
        """ Returns executed datetime range """

    @abstractmethod
    def get_trigger_schedule(self):
        pass

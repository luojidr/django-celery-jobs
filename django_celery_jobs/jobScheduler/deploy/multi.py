import os
import warnings
from django.utils.functional import cached_property

from .celeryd import CelerydDeploy
from ..core.enums.deploy import DeployModeEnum

__all__ = ['MultiDeploy']


class MultiDeploy(CelerydDeploy):
    """  Manage workers """
    MODE = DeployModeEnum.MULTI.name.lower()

    def __init__(self, wn=None):
        super().__init__()
        self._wn = wn or os.cpu_count() // 2

        broker_url = self.celery_app.conf.broker_url
        if broker_url.startswith('amqp://'):
            warnings.warn("Warning pyamqp://... is recommended for BROKER_URL, Otherwise, errors maybe occur like:"
                          "\n\tTypeError: cannot pickle 'memoryview' object, or \n"
                          "\n\tSystemError: <method '_basic_recv' of '_librabbitmq.Connection' objects> "
                          "returned a result with an error set")

    @property
    def command(self):
        """ No need to implement """
        raise NotImplementedError

    def start(self):
        return "{celerypath} multi start {n} -A {app} {args}".format(
            celerypath=self.celerypath, n=self._wn,
            app=self.app_module, args=self._w_entry.args
        )

    def restart(self):
        pass

    def stop(self):
        pass

    def kill(self):
        pass


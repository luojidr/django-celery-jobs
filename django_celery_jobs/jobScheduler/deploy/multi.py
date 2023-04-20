import os
import warnings

from .celeryd import CelerydDeploy
from ..core.exceptions import OptionError
from ..core.enums.deploy import DeployModeEnum

__all__ = ['MultiDeploy']


class MultiDeploy(CelerydDeploy):
    """  Manage workers
    For production deployments you should be using init-scripts or a process supervision system
    """
    MODE = DeployModeEnum.MULTI.name.lower()

    def __init__(self, wn=None):
        super().__init__()
        wn = wn or os.cpu_count() // 2
        self._wns = " ".join(['w%s' % i for i in range(1, wn + 1)])

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

    def _check(self):
        w_option = self._w_entry.named_option
        # logfile: /var/log/celery/%n%I.log
        if not w_option.has_option('f', alias='logfile'):
            raise OptionError('Command multi must be have `logfile`')

        # pidfile: /var/run/celery/%n.pid
        if not w_option.has_option('pidfile'):
            raise OptionError('Command multi must be have `pidfile`')

    def _run(self, cmd, is_opts=True):
        self._check()

        if is_opts:
            w_options = self._w_entry.options
        else:
            w_options = []

        return "{celerypath} multi {cmd} {wns} -A {app} {options}".format(
            celerypath=self.celerypath, wns=self._wns,
            cmd=cmd, app=self.app_module, options=' '.join(w_options)
        )

    def start(self):
        self._run(cmd='start')

    def restart(self):
        self._run(cmd='restart')

    def stop(self):
        self._run(cmd='stop', is_opts=False)

    def kill(self):
        self._run(cmd='kill', is_opts=False)


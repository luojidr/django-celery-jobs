from itertools import chain

from .base import BaseDeploy
from ..core.enums.deploy import DeployModeEnum

__all__ = ['CelerydDeploy']


class EntryPoint(BaseDeploy):
    def _get_command_argv(self, alias=None):
        cmd_argv = []
        mode = alias or self.MODE
        options = self.get_options(mode=mode)

        for option in options:
            name = option['name']
            value = option['value']
            cmd_argv.append((name, value))

        return cmd_argv

    @property
    def command(self):
        args = [(self.MODE,)]
        args.extend(self.options)
        return " ".join(chain.from_iterable(args))

    @property
    def options(self):
        argv = self._get_command_argv(alias=self.MODE)
        return chain.from_iterable(argv)


class WorkerEntryPoint(EntryPoint):
    MODE = DeployModeEnum.WORKER.name.lower()


class BeatEntryPoint(EntryPoint):
    MODE = DeployModeEnum.BEAT.name.lower()


class CelerydDeploy(BaseDeploy):
    """  Manage worker or beat """
    MODE = DeployModeEnum.CELERYD.name.lower()

    def __init__(self):
        self._b_entry = BeatEntryPoint()
        self._w_entry = WorkerEntryPoint()

        self._options = self.get_options(mode=self.MODE)

    @property
    def celerypath(self):
        return self._options['celerypath']['value']

    @property
    def worker(self):
        return "{celerypath} -A {app} {cmd}".format(
            celerypath=self.celerypath,
            app=self.app_module, cmd=self._w_entry.command
        )

    @property
    def beat(self):
        return "{celerypath} -A {app} {cmd}".format(
            celerypath=self.celerypath,
            app=self.app_module, cmd=self._b_entry.command
        )

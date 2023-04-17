from collections import namedtuple

from ..core.exceptions import OptionError
from .options import WORKER, BEAT, SUPERVISOR

Option = namedtuple('Option', ["name", "alias", "help"])


class NamedOption:
    OPTION_ALIAS = {
        'beat': BEAT,
        'worker': WORKER,
        'supervisor': SUPERVISOR,
    }

    def __init__(self, alias):
        self._alias = alias

        for option in self.OPTION_ALIAS[self._alias]:
            name = option[0].strip('-')
            setattr(self, name, Option(*option))


class BaseDeploy:
    def __init__(self, alias_option, **kwargs):
        self._option = NamedOption(alias_option)
        super().__init__(**kwargs)

    def _check_option(self, name):
        if name not in self._option.__dict__:
            raise OptionError('Option %s is valid' % name)

    @property
    def worker(self):
        pass

    @property
    def beat(self):
        pass


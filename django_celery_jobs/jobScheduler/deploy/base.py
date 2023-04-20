import six
from abc import ABCMeta, abstractmethod
from collections import namedtuple, OrderedDict

from django.utils.functional import cached_property

from ..core.celery.utils import get_app_module, get_celery_app
from ..core.exceptions import OptionError, DuplicatedError
from .options import CELERYD, WORKER, BEAT, SUPERVISOR
from django_celery_jobs.models import DeployOptionModel

Option = namedtuple('Option', ["name", "alias", "help"])

__all__ = ['NamedOption', 'BaseDeploy']


class NamedOption:
    OPTION_ALIAS = {
        'beat': BEAT,
        'worker': WORKER,
        'celeryd': CELERYD,
        'supervisor': SUPERVISOR,
    }

    def __init__(self, alias):
        self._alias = alias

        for option in self.OPTION_ALIAS[self._alias]:
            name = option[0].strip('-')
            setattr(self, name, Option(*option))

    def has_option(self, name, alias=None):
        try:
            if not hasattr(self, name):
                getattr(self, str(alias))
        except AttributeError:
            return False

        return True


class BaseDeploy(six.with_metaclass(ABCMeta)):
    MODE = None

    @property
    def app_module(self):
        options = self.get_options(mode=self.MODE)
        return options.get('A', {}).get('value') or get_app_module()

    @cached_property
    def celery_app(self):
        return get_celery_app()

    @property
    def command(self):
        """ Celery command """
        raise NotImplementedError

    @cached_property
    def named_option(self):
        """ NamedOption """
        return NamedOption(alias=self.MODE)

    def get_options(self, mode):
        options = OrderedDict()
        queryset = DeployOptionModel.get_options_by_mode(mode)

        for obj in queryset:
            name = obj.name
            key = name.strip('-')

            if key not in self.named_option.__dict__:
                raise OptionError('Option %s is valid' % key)

            if key in options:
                raise DuplicatedError('Option %s to %s is duplicated.' % (key, self.MODE))

            options[key] = dict(
                name=name, alias=obj.alias,
                value=obj.value, description=obj.description
            )

        return options

    def deploy(self):
        """ Deploy using the bash command """
        raise NotImplementedError

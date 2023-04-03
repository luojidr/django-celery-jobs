import logging
import importlib
import traceback

from django.conf import settings
from celery import current_app
from celery.exceptions import ImproperlyConfigured

_default_app = None


def get_celery_app():
    global _default_app

    if _default_app is not None:
        return _default_app

    try:
        app_path = settings.CELERY_APP
        pkg_name, app_name = app_path.split(":", 1)

        module = importlib.import_module(pkg_name)
        _default_app = getattr(module, app_name, current_app)
    except (AttributeError, ValueError, ModuleNotFoundError):
        logging.error("import celery app is failed from <%s>", app_path)
        logging.error(traceback.format_exc())
        _default_app = current_app

    if _default_app.conf.broker_url is None:
        raise ImproperlyConfigured("Celery instance is empty, recommended set `CELERY_APP`")

    return _default_app

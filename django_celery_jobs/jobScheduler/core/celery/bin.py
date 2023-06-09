import logging
import platform
import traceback
from itertools import chain

from django.utils.functional import cached_property
from celery.apps.beat import Beat

from .utils import get_celery_app, get_app_module


class BaseService:
    IS_WINDOWS = platform.system() == 'Windows'

    def __init__(self, scheduler=None, app=None, loglevel=None, concurrency=None, **opts):
        self.scheduler = scheduler

        self._app = app
        self.loglevel = loglevel or "INFO"
        self.concurrency = concurrency or 1

    @cached_property
    def app_module(self):
        return get_app_module()

    def start(self):
        raise NotImplementedError

    def shutdown(self, wait=True):
        raise NotImplementedError

    @property
    def pool(self):
        if self.IS_WINDOWS:
            pool = 'threads'
        else:
            try:
                import gevent as pool_pkg
            except ModuleNotFoundError:
                try:
                    import eventlet as pool_pkg
                except ModuleNotFoundError:
                    pool_pkg = None

            pool = pool_pkg and pool_pkg.__package__ or 'threads'

        return pool

    @property
    def celery_app(self):
        return self._app or get_celery_app()


class LocalWorkerService(BaseService):
    _command = 'worker'

    def start(self):
        """ Best use celery multi command
        Cmd: celery -A celery_jobs_demo.celery worker -l info -P gevent --concurrency=50 -n worker1@%%h
        """
        app = self.celery_app
        argv_list = [
            ('-A', self.app_module),
            (self._command, ),
            ('-P', self.pool),
            ('-l', self.loglevel),
            ('-c', str(self.concurrency)),
        ]

        if not self.IS_WINDOWS:
            argv_list.append(('-D', ))

        try:
            app.worker_main(argv=list(chain.from_iterable(argv_list)))
        except Exception as exc:
            logging.error(traceback.format_exc())

    def shutdown(self, wait=True):
        pass

    def run_worker(self):
        """ celery.apps.worker:Worker """
        app = self.celery_app
        worker = app.Worker(concurrency=self.concurrency, loglevel=self.loglevel, pool=self.pool)
        worker.start()


class LocalBeatService(BaseService):
    _command = 'beat'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loglevel = kwargs.get('loglevel', 'DEBUG')
        self.detach = bool(kwargs.get('detach'))
        self.beat_scheduler = kwargs.get('beat_scheduler')
        self.max_interval = kwargs.get('max_interval')  # Default interval 5s

    def start(self):
        app = self.celery_app
        argv_list = [
            ('-A', self.app_module),
            (self._command, ),
            ('-l', self.loglevel),
        ]

        if self.beat_scheduler:
            argv_list.append(('-S', self.beat_scheduler))

        if self.max_interval:
            argv_list.append(('--max-interval', str(self.max_interval)))

        if self.detach:
            argv_list.append(('--detach', ))

        try:
            app.start(argv=list(chain.from_iterable(argv_list)))
        except Exception as exc:
            logging.error(traceback.format_exc())

    def shutdown(self, wait=True):
        pass

    def run_beat(self):
        """ celery.apps.beat:Beat """
        app = self.celery_app
        beat_options = dict(app=app, max_interval=self.max_interval or 5, loglevel=self.loglevel)
        self.beat_scheduler and beat_options.update(scheduler_cls=self.beat_scheduler)

        beat = Beat(**beat_options)
        beat.run()

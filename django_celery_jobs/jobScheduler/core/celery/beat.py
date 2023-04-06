"""
1. A new task can never be dynamically added after the worker command starts, eg:
    celery -A config.celery worker -l info -P gevent --concurrency=10 -n worker1@%%h
2. Periodic tasks in your own projects don't need to be set up in `app.conf.beat_schedule`
3. Periodic tasks in other people's projects, they will maintain the worker deployment themselves,
   you only need to perform tasks periodically with beat command.
   Therefore, you must customize the Beat class to perform the new scheduled task.
"""

import socket
import logging

from celery import platforms
from celery.apps.beat import Beat as CeleryBeat

__all__ = ('MyBeat',)

logger = logging.getLogger('celery.beat')


class MyBeat(CeleryBeat):
    service_instance = None
    SCHEDULER_CLS = '%s.scheduler:BeatScheduler' % __name__.rsplit('.', 1)[0]

    def start_scheduler(self):
        if self.pidfile:
            platforms.create_pidlock(self.pidfile)

        service = self.get_service()
        print(self.banner(service))

        self.setup_logging()
        if self.socket_timeout:
            logger.debug('Setting default socket timeout to %r',
                         self.socket_timeout)
            socket.setdefaulttimeout(self.socket_timeout)
        try:
            self.install_sync_handler(service)
            service.start()
        except Exception as exc:
            logger.critical('beat raised exception %s: %r',
                            exc.__class__, exc,
                            exc_info=True)
            raise

    def get_service(self):
        logger.info("MyBeat => scheduler ->: %s", self.scheduler_cls)

        if self.service_instance is None:
            service = self.Service(
                app=self.app,
                max_interval=self.max_interval,
                scheduler_cls=self.SCHEDULER_CLS,
                schedule_filename=self.schedule,
            )
            self.service_instance = service

        return self.service_instance

    CeleryBeat.get_service = get_service
    CeleryBeat.start_scheduler = start_scheduler
    CeleryBeat.SCHEDULER_CLS = SCHEDULER_CLS
    CeleryBeat.service_instance = service_instance

from enum import Enum


class DeployModeEnum(Enum):
    # cmd: worker -l info -c 1 -P threads ...
    WORKER = (1, 'worker')

    # cmd:  beat -l info ...
    BEAT = (2, 'beat')

    # Blocking start worker instance or the beat periodic task scheduler.
    # cmd: celery -A proj [worker|beat] COMMAND [ARGS]...
    CELERYD = (3, 'celeryd')

    # https://docs.celeryq.dev/en/latest/reference/celery.bin.multi.html
    # Start multiple worker instances for worker, only to worker
    MULTI = (4, 'multi')

    # https://docs.celeryq.dev/en/latest/userguide/daemonizing.html#generic-init-scripts
    # generic bash init-scripts for the celery worker or beat program
    INIT_SCRIPT = (5, 'init-script')

    # https://docs.celeryq.dev/en/latest/userguide/daemonizing.html#usage-systemd
    # Use `systemctl` command to start worker or beat
    SYSTEMD = (6, 'systemd')

    # https://docs.celeryq.dev/en/latest/userguide/daemonizing.html#supervisor
    # Use python third package to manage the celery worker or beat
    SUPERVISOR = (7, 'supervisor')

    @property
    def mode(self):
        return self.value[0]

    @property
    def desc(self):
        return self.value[1]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())

    @classmethod
    def members(cls):
        return [(_enum.mode, _enum.desc) for _enum in cls._member_map_.values()]

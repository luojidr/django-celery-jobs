import socket
import croniter

from django.utils import timezone


def get_ip_addr():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


def get_trigger_next_range(trigger, start_time=None, run_times=None):
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    cron_expr = trigger.expression
    start_time = start_time or timezone.datetime.now()

    cron_expr_list = [s.strip() for s in cron_expr.split(" ") if s.strip()]
    if len(cron_expr_list) != 5:
        raise ValueError(f'Cron表达式<{cron_expr}>格式错误')

    if isinstance(start_time, (str, bytes)):
        start_time = timezone.datetime.strptime(start_time, dt_fmt)

    run_time_list = []
    max_times = int(run_times or 10)
    cron = croniter.croniter(" ".join(cron_expr_list), start_time=start_time)

    # The latest 10 execution times
    for i in range(run_times):
        next_run_time = cron.get_next(timezone.datetime)
        run_time_list.append(next_run_time.strftime(dt_fmt))

    return run_time_list

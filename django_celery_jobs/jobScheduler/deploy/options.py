CELERYD = [
    ('celerypath', '', "Execute celery location"),
    ('-A', '-app', "celery app module in Project"),
]

WORKER = [
        ('-n', '--hostname', "Set custom hostname (e.g., 'w1@%%h'). "
                             "Expands: %%h (hostname), %%n (name) and %%d,(domain)"),
        ('-D', '--detach', "Start worker as a background process."),
        ('-l', '--loglevel', "[DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL]"),
        ('-O', '', "Apply optimization profile."),
        ('--prefetch-multiplier', '', "Set custom prefetch multiplier value for this worker instance."),
        ('-c', '--concurrency', "Number of child processes processing the queue.  "
                                "The default is the number of CPUs available on your system."),
        ('-P', '--pool', "[prefork|eventlet|gevent|solo|processes|threads]"),
        ('-E', '--task-events, --events', "Send task-related events that can be "
                                          "captured by monitors like celery events,celerymon, and others."),
        ('--time-limit', '', "FLOAT Enables a hard time limit (in seconds int/float) for tasks."),
        ('--soft-time-limit', '', "FLOAT Enables a soft time limit (in seconds int/float) for tasks"),
        ('--max-tasks-per-child', '', "INTEGER Maximum number of tasks a pool worker can "
                                      "execute before it's terminated and replaced by a new worker."),
        ('--max-memory-per-child', '', "INTEGER Maximum amount of resident memory, in KiB, that may be consumed "
                                       "by a child process before it will be replaced by a new one. If a single task "
                                       "causes a child process to exceed this limit, the task will be completed "
                                       "and the child process will be replaced afterwards. Default: no limit."),
        ('-Q', '--queues', "COMMA SEPARATED LIST"),
        ('-X', '--exclude-queues', "COMMA SEPARATED LIST"),
        ('-I', '--include', "COMMA SEPARATED LIST"),
        ('-f', '--logfile', "TEXT"),
        ('--pidfile', '', 'TEXT'),
    ]

BEAT = [
    ('--detach', '', "Detach and run in the background as a daemon."),
    ('-S', '--scheduler', "Scheduler class to use"),
    ('--max-interval', '', "INTEGER Max seconds to sleep between schedule iterations"),
    ('-l', '--loglevel', "[DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL]"),
    ('-f', '--logfile', "TEXT"),
    ('--pidfile', '', 'TEXT'),
]

MULTI = [
    ('--pidfile', '', "eg: /var/run/celery/%n.pid"),
    ('--logfile', '', "eg: /var/log/celery/%n%I.log"),
]

# https://github.com/Supervisor/supervisor/blob/main/supervisor/skel/sample.conf
SUPERVISOR = [
    ('command', '', "Set full path to celery program if using virtualenv"),
    ('directory', '', "Directory should become before command"),
    ('autostart ', '', "default true, The supervisord also starts automatically when it is started up"),
    ('autorestart', '', "default true, The program restarts automatically after an abnormal exit"),
    ('startretries', '', "default 3, Number of automatic retries after startup failure"),
    ('startsecs', '', "If no exception is found 5 seconds after startup, the startup is normal"),
    ('stdout_logfile ', '', "stdout log path, NONE for none; default AUTO"),
    ('stderr_logfile ', '', "stderr log path, NONE for none; default AUTO"),
    ('user', '', "Which user starts"),
    ('numprocs', '', "default 1, number of processes copies to start (def 1)"),
    ('process_name', '', "process_name=%(program_name)s, expr (default %(program_name)s)"),
]

class AlreadyRunningError(Exception):
    pass


class NotRunningError(Exception):
    pass


class CeleryAppError(Exception):
    pass


class JobLookupError(KeyError):
    def __init__(self, name):
        super(JobLookupError, self).__init__(u'No job by name of %s was found' % name)


class OptionError(Exception):
    pass

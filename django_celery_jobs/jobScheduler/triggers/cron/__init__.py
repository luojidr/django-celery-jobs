from datetime import datetime, timedelta
from tzlocal import get_localzone
import six

from .fields import BaseField, MonthOfYearField, DayOfMonthField, DayOfWeekField
from ...util import datetime_ceil, convert_to_datetime, datetime_repr, astimezone, localize, normalize


class CronTrigger:
    """ Specified time constraints, similarly to how the UNIX cron scheduler works

    :param int|str minute: minute (0-59) or * (Per minute)
    :param int|str hour: hour (0-23) or * (Per hour)
    :param int|str day_of_week: number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun) or * (Per week)
    :param int|str day_of_month: number of day (1-31) or *  (Per day)
    :param int|str month_of_year: number of month (1-12) or *  (Per month)
    :param datetime.tzinfo|str timezone: time zone to use for the date/time calculations (defaults
        to scheduler timezone)
    """

    FIELD_NAMES = ('minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')
    FIELDS_MAP = {
        'minute': BaseField,
        'hour': BaseField,
        'day_of_week': DayOfWeekField,
        'day_of_month': DayOfMonthField,
        'month_of_year': MonthOfYearField,
    }

    __slots__ = 'timezone', 'fields'

    def __init__(self, minute=None, hour=None, day_of_week=None, day_of_month=None, month_of_year=None,
                 timezone=None):
        self.timezone = timezone
        values = dict((key, value) for (key, value) in six.iteritems(locals()) if key in self.FIELD_NAMES)

        self.fields = []
        assign_defaults = False

        for field_name in self.FIELD_NAMES:
            is_default = False
            expr = values.pop(field_name)

            if expr is None:
                expr = '*'
                is_default = False

            field_class = self.FIELDS_MAP[field_name]
            field = field_class(field_name, expr, is_default)
            self.fields.append(field)

    @classmethod
    def from_crontab(cls, expr, timezone=None):
        """ Create a :class:`~CronTrigger` from a standard crontab expression.

        :return: a :class:`~CronTrigger` instance
        """
        values = expr.split()
        if len(values) != 5:
            raise ValueError('Wrong number of fields; got {}, expected 5'.format(len(values)))

        return cls(minute=values[0], hour=values[1], day_of_week=values[2],
                   day_of_month=values[3], month_of_year=values[4], timezone=timezone)

    def _increment_field_value(self, dateval, fieldnum):
        """
        Increments the designated field and resets all less significant fields to their minimum
        values.

        :type dateval: datetime
        :type fieldnum: int
        :return: a tuple containing the new date, and the number of the field that was actually
            incremented
        :rtype: tuple
        """

        values = {}
        i = 0
        while i < len(self.fields):
            field = self.fields[i]
            if not field.REAL:
                if i == fieldnum:
                    fieldnum -= 1
                    i -= 1
                else:
                    i += 1
                continue

            if i < fieldnum:
                values[field.name] = field.get_value(dateval)
                i += 1
            elif i > fieldnum:
                values[field.name] = field.get_min(dateval)
                i += 1
            else:
                value = field.get_value(dateval)
                maxval = field.get_max(dateval)
                if value == maxval:
                    fieldnum -= 1
                    i -= 1
                else:
                    values[field.name] = value + 1
                    i += 1

        difference = datetime(**values) - dateval.replace(tzinfo=None)
        return normalize(dateval + difference), fieldnum

    def _set_field_value(self, dateval, fieldnum, new_value):
        values = {}
        for i, field in enumerate(self.fields):
            if field.REAL:
                if i < fieldnum:
                    values[field.name] = field.get_value(dateval)
                elif i > fieldnum:
                    values[field.name] = field.get_min(dateval)
                else:
                    values[field.name] = new_value

        return localize(datetime(**values), self.timezone)

    def get_next_fire_time(self, previous_fire_time, now):
        if previous_fire_time:
            start_date = min(now, previous_fire_time + timedelta(microseconds=1))
            if start_date == previous_fire_time:
                start_date += timedelta(microseconds=1)
        else:
            start_date = max(now, self.start_date) if self.start_date else now

        fieldnum = 0
        next_date = datetime_ceil(start_date).astimezone(self.timezone)
        while 0 <= fieldnum < len(self.fields):
            field = self.fields[fieldnum]
            curr_value = field.get_value(next_date)
            next_value = field.get_next_value(next_date)

            if next_value is None:
                # No valid value was found
                next_date, fieldnum = self._increment_field_value(next_date, fieldnum - 1)
            elif next_value > curr_value:
                # A valid, but higher than the starting value, was found
                if field.REAL:
                    next_date = self._set_field_value(next_date, fieldnum, next_value)
                    fieldnum += 1
                else:
                    next_date, fieldnum = self._increment_field_value(next_date, fieldnum)
            else:
                # A valid value was found, no changes necessary
                fieldnum += 1

            # Return if the date has rolled past the end date
            if self.end_date and next_date > self.end_date:
                return None

        if fieldnum >= 0:
            next_date = self._apply_jitter(next_date, self.jitter, now)
            return min(next_date, self.end_date) if self.end_date else next_date

    def __str__(self):
        options = ["%s='%s'" % (f.name, f) for f in self.fields if not f.is_default]
        return 'cron[%s]' % (', '.join(options))

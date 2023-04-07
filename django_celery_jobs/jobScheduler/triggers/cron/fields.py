import re
import six
from calendar import monthrange

from .expressions import (
    AllExpression, RangeExpression,
    WeekdayPositionExpression, LastDayOfMonthExpression,
    WeekdayRangeExpression, MonthRangeExpression
)

__all__ = (
    'MIN_VALUES', 'MAX_VALUES',
    'BaseField', 'DayOfMonthField', 'DayOfWeekField', 'MonthOfYearField'
)

MIN_VALUES = {'day_of_month': 1, 'month_of_year': 1, 'day_of_week': 0, 'hour': 0, 'minute': 0}
MAX_VALUES = {'day_of_month': 31, 'month_of_year': 12, 'day_of_week': 6, 'hour': 23, 'minute': 59}
SEPARATOR = re.compile(' *, *')


class BaseField(object):
    REAL = True
    COMPILERS = [AllExpression, RangeExpression]

    def __init__(self, name, expr, is_default=False):
        self.name = name
        self.is_default = is_default
        self.compile_expressions(expr)

    def get_min(self, dateval):
        return MIN_VALUES[self.name]

    def get_max(self, dateval):
        return MAX_VALUES[self.name]

    def get_value(self, dateval):
        return getattr(dateval, self.name)

    def get_next_value(self, dateval):
        smallest = None
        for expr in self.expressions:
            value = expr.get_next_value(dateval, self)
            if smallest is None or (value is not None and value < smallest):
                smallest = value

        return smallest

    def compile_expressions(self, expr):
        self.expressions = []

        for _expr in SEPARATOR.split(str(expr).strip()):
            self.compile_expression(_expr)

    def compile_expression(self, expr):
        for compiler in self.COMPILERS:
            match = compiler.value_re.match(expr)
            if match:
                compiled_expr = compiler(**match.groupdict())

                try:
                    compiled_expr.validate_range(self.name)
                except ValueError as e:
                    exc = ValueError('Error validating expression {!r}: {}'.format(expr, e))
                    six.raise_from(exc, None)

                self.expressions.append(compiled_expr)
                return

        raise ValueError('Unrecognized expression "%s" for field "%s"' % (expr, self.name))

    def __str__(self):
        expr_strings = (str(e) for e in self.expressions)
        return ','.join(expr_strings)


class DayOfWeekField(BaseField):
    REAL = False
    COMPILERS = BaseField.COMPILERS + [WeekdayRangeExpression]

    def get_value(self, dateval):
        return dateval.weekday()


class DayOfMonthField(BaseField):
    COMPILERS = BaseField.COMPILERS + [WeekdayPositionExpression, LastDayOfMonthExpression]

    def get_max(self, dateval):
        return monthrange(dateval.year, dateval.month)[1]


class MonthOfYearField(BaseField):
    COMPILERS = BaseField.COMPILERS + [MonthRangeExpression]

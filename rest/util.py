import pytz
import datetime
from django.utils.dateparse import parse_datetime


def utc_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def get_valid_period(start_time=None, end_time=None):
    """
    Extract a valid period.

    If start_time and end_time are provided and no more than a day apart, return them.
    If neither start_time nor end_time are given, return the previous 24 hour period, calculated from now.
    If start_time is given, return 24 hour period starting from start time.
    If end_time is given, return 24 hour period ending at end_time.

    :param start_time:
    :param end_time:
    :return:
    """
    if start_time and end_time:
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        # Allow 1 day and 1 hour to not bother with more complicated logic for daylight savings time edge cases:
        if start_time + datetime.timedelta(days=1, hours=1) < end_time:
            raise ValueError("Difference between start_time and end_time must not be greater than one day")

        return start_time, end_time

    if start_time is None and end_time is None:
        end_time = utc_now()

    day = datetime.timedelta(days=1)
    if start_time:
        return start_time, start_time + day
    else:
        return end_time - day, end_time

import pytz
import datetime

def utc_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

def day_period(start_time=None, end_time=None):
    if (start_time and end_time) or (start_time is None and end_time is None):
        raise ValueError("One and only one of start_time or end_time should be provided")
    day = datetime.timedelta(days=1)
    if start_time:
        return start_time, start_time + day
    else:
        return end_time - day, end_time

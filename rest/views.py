from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime

from .models import history as json_history
from .util import utc_now, day_period


@api_view()
def history(request, country, start_time=None, end_time=None):
    start_time = extract_datetime_param(request, 'start_time')
    end_time = extract_datetime_param(request, 'end_time')

    if start_time and end_time:
        raise ParseError("Only one of start_time or end_time should be provided")
    if start_time is None and end_time is None:
        end_time = utc_now()

    start, end = day_period(start_time, end_time)
    data = json_history(start, end, country)
    response = Response(data)
    response['Content-Length'] = len(data)
    return Response(data)

def extract_datetime_param(request, param_name):
    time = request.query_params.get(param_name, None)
    if time is None:
        return None

    parsed = parse_datetime(time)
    if parsed is None:
        raise ParseError("Unable to extract datetime value from {} parameter".format(param_name))

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        message = "The {} parameter should be specified with a timezone and URL encoded, for example 2016-01-20T16:08:07%2B02:00"
        raise ParseError(message.format(param_name))

    return parsed


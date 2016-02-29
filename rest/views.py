from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework import generics
from django.utils.dateparse import parse_datetime

from rphistory.models import Song
from .models import json_history_count_vector, json_history_date_period
from .serializers import UnmatchedSongsSerializer
from .util import utc_now, get_valid_period


@api_view()
def history(request, country):
    base_time, count_vector = extract_time_vector(request)
    if base_time:
        data = json_history_count_vector(country, base_time, count_vector)
    else:
        start_time = extract_datetime_param(request, 'start_time')
        end_time = extract_datetime_param(request, 'end_time')
        try:
            start, end = get_valid_period(start_time, end_time)
        except ValueError as e:
            raise ValidationError({'error': str(e)})

        data = json_history_date_period(country, start, end)

    response = Response(data)
    response['Content-Length'] = len(data)
    return Response(data)


class UnmatchedSongList(generics.ListAPIView):
    queryset = Song.unmatched.all()
    serializer_class = UnmatchedSongsSerializer

    def list(self, request, country):
        order = request.query_params.get('order', None)
        if order == 'artist':
            order = 'artists__name'
        elif order == 'played':
            pass
        else:
            order = 'id'

        queryset = self.get_queryset().in_country(country).artists().album().with_order_by(order)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


def extract_time_vector(request):
    """
    Extract base time and directional count from request, if present.

    A directional count of 50 means get 50 newer items, -50 means get 50 older items.
    :param request:
    :return:
    """
    base_time = extract_datetime_param(request, 'base_time')
    if not base_time:
        return (None, None)

    count_vector = request.query_params.get('count_vector')
    if count_vector is None:
        count_vector = 200
    else:
        try:
            count_vector = int(count_vector)
        except ValueError:
            raise ValidationError({'error': 'count_vector parameter should be a positive or negative base 10 integer'})

    return (base_time, count_vector)


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

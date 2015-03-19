from logging import getLogger
from django.contrib.gis.geoip import GeoIP
from django.shortcuts import render_to_response
from django.template.context_processors import csrf
from django.utils import timezone
from dateutil.parser import parse
from ipware.ip import get_real_ip
import pytz
from trackmap.models import Track
from trackmap.forms import PlaylistOptions
from trackmap.settings import (
    TRACKMAP_SESSION_EXPIRY, TRACKMAP_SESSION_RENEW_WHEN_SECONDS_LEFT, TRACKMAP_DEFAULT_COUNTRY,
    TRACKMAP_DEFAULT_TIMEZONE, TRACKMAP_DEFAULT_TRACK_LIMIT,
)


log = getLogger(__name__)


def get_submitted_params(request, param_names):
    params = {}
    for param in param_names:
        value = request_value(request, param)
        if value is not None:
            params[param] = value
    return params


def request_value(request, key, default=None):
    """
    Returns first found value, using this order: POST, GET, default.
    :param request:
    :param key:
    :param default:
    :return:
    """

    value = request.POST.get(key, None) or request.GET.get(key, None)
    if value is not None:
        return value
    return default


def get_visitor_country(request):
    ip = get_real_ip(request)
    if ip:
        return GeoIP().country(ip)['country_code']
    return None

def get_utc_start_time(start_time, user_timezone):
    """
    Gets the utc time for the given time.

    If start_time is a naive time, it will localized according the user_timezone.
    If start_time is a timezone-aware time, user_timezone is ignored.

    :param string start_time: parseable datetime string
    :param string user_timezone: string of timezone known to pytz (e.g. 'America/Los_Angeles')
    :return: datetime (or None, if unable to parse datetime or timezone)
    """
    time = None
    if start_time:
        try:
            time = parse(start_time)
            if timezone.is_naive(time):
                user_tz = pytz.timezone(user_timezone)
                time = user_tz.localize(time)

            time = time.astimezone(pytz.utc)
        except ValueError:
            pass

    return time

def keep_session_alive(session):
    if session.get_expiry_age() < TRACKMAP_SESSION_RENEW_WHEN_SECONDS_LEFT:
        session.set_expiry(TRACKMAP_SESSION_EXPIRY)


def default_country(request):
    country = get_visitor_country(request)
    if not country:
        country = TRACKMAP_DEFAULT_COUNTRY
    return country


class Param(object):

    @staticmethod
    def update_values(params, data):
        for param in params:
            param.set_value(data)

    @staticmethod
    def values_if_set(params):
        values = {}
        for param in params:
            if param.value_set:
                values[param.name] = param.value
        return values

    @staticmethod
    def persist_values(params):
        for param in params:
            param.save_value_in_session()

    def __init__(self, name, request, store_in_session=True, fetch_from_session=True, default=None, set_default=True):
        self.name = name
        self.request = request
        self.store_in_session = store_in_session
        self.fetch_from_session = fetch_from_session
        self.default = default
        self.set_default = set_default
        self._value = None
        self.value_set = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.value_set = True

    def set_value(self, data):
        if self.name in data:
            self.value = data[self.name]
            return

        if self.fetch_from_session:
            session = self.request.session
            if self.name in session:
                self.value = session[self.name]
                data[self.name] = self.value
                return

        if self.set_default and self.name not in data:
            if hasattr(self.default, '__call__'):
                value = self.default(self.request)
            else:
                value = self.default
            self.value = value
            data[self.name] = self.value

    def save_value_in_session(self):
        if self.store_in_session and self.value_set:
            session = self.request.session
            old_value = session.get(self.name, None)
            if not old_value == self.value:
                session[self.name] = self.value


def playlist(request):
    template_name = "trackmap/playlist.html"

    keep_session_alive(request.session)

    limit = Param('limit', request, default=TRACKMAP_DEFAULT_TRACK_LIMIT)
    timezone = Param('timezone', request, default=TRACKMAP_DEFAULT_TIMEZONE)
    country = Param('country', request, default=default_country)
    start_time = Param('start_time', request, store_in_session=False, fetch_from_session=False, set_default=False)
    params = [limit, timezone, country, start_time]

    param_data = get_submitted_params(request, ['limit', 'timezone', 'country', 'start_time'])

    Param.update_values(params, param_data)
    values = Param.values_if_set(params)

    form = PlaylistOptions(values)
    if not form.errors:
        Param.persist_values(params)

    # TODO: use foundation form in the template instead of li form

    # TODO: validate start_time (in form)

    context = {p.name: p.value for p in params}
    context['form'] = form
    context.update(csrf(request))

    time = get_utc_start_time(start_time.value, timezone.value)

    tracks = Track.objects.get_available_tracks(country.value, start_time=time, limit=limit.value)

    if tracks:
        context['playlist_uri'] = 'spotify:trackset:RadioParadisePlaylist:{}'.format(
            ','.join(track.spotify_id for track in tracks))

    return render_to_response(template_name, context)

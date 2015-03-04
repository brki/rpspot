from logging import getLogger
from django.conf import settings
from django.contrib.gis.geoip import GeoIP
from django.views.generic.base import TemplateView
from django.utils import timezone
from dateutil.parser import parse
from ipware.ip import get_real_ip
from pytz import utc
from trackmap.models import Track


log = getLogger(__name__)


class PlaylistView(TemplateView):

    template_name = "trackmap/playlists.html"

    def get_context_data(self, **kwargs):
        context = super(PlaylistView, self).get_context_data(**kwargs)

        self.set_session_data()

        start_time = self.request_value('start_time')
        if start_time:
            try:
                start_time = parse(start_time)
                if timezone.is_naive(start_time):
                    start_time = start_time.replace(tzinfo=utc)
                else:
                    start_time = start_time.astimezone(utc)
            except ValueError:
                start_time = None

        session = self.request.session
        country = session['country']
        context['tracks'] = Track.objects.get_available_tracks(
            country, start_time=start_time, limit=session['limit'])
        context['playlist_uri'] = 'spotify:trackset:RadioParadisePlaylist:{}'.format(
            ','.join(track.spotify_id for track in context['tracks'])
        )
        context['country'] = country
        context['is_country_known'] = session['is_country_known']
        context['session'] = self.request.session
        return context

    def set_session_data(self):
        session = self.request.session
        limit = self.request_value('limit') or session.get('limit', None) or settings.TRACKMAP_DEFAULT_TRACK_LIMIT
        country = self.request_value('country')
        timezone = self.request_value('timezone') or session.get('timezone') or settings.TRACKMAP_DEFAULT_TIMEZONE

        is_country_known = country is not None or session.get('is_country_known', False)
        if not country:
            country = session.get('country', None)
        if not country:
            country = self.get_visitor_country()
            if country:
                is_country_known = True
            else:
                country = settings.TRACKMAP_DEFAULT_COUNTRY

        self.set_session_value('country', country)
        self.set_session_value('is_country_known', is_country_known)
        self.set_session_value('limit', limit)
        self.set_session_value('timezone', timezone)

    def get_visitor_country(self):
        ip = get_real_ip(self.request)
        if ip:
            return GeoIP().country(ip)['country_code']
        return None

    def request_value(self, key, default=None):
        value = self.request.POST.get(key, None) or self.request.GET.get(key, None)
        if value is not None:
            return value
        return default

    def set_session_value(self, key, value):
        old_value = self.request.session.get(key, None)
        if not old_value == value:
            self.request.session[key] = value

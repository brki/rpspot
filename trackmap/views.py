from django.views.generic.base import TemplateView
from django.utils import timezone
from dateutil.parser import parse
from pytz import utc
from trackmap.models import Track


class PlaylistView(TemplateView):

    template_name = "trackmap/playlists.html"

    def get_context_data(self, **kwargs):
        context = super(PlaylistView, self).get_context_data(**kwargs)
        country = 'CH'

        start_time = self.request.GET.get('start_time', None)
        if start_time:
            try:
                start_time = parse(start_time)
                if timezone.is_naive(start_time):
                    start_time = start_time.replace(tzinfo=utc)
                else:
                    start_time = start_time.astimezone(utc)
            except ValueError:
                start_time = None

        limit = self.request.GET.get('limit', 14)
        context['tracks'] = Track.objects.get_available_tracks(country, start_time=start_time, limit=limit)
        context['playlist_uri'] = 'spotify:trackset:RadioParadisePlaylist:{}'.format(
            ','.join(track.spotify_id for track in context['tracks'])
        )
        return context

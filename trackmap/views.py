from django.views.generic.base import TemplateView

from trackmap.models import Track

class PlaylistView(TemplateView):

    template_name = "trackmap/playlists.html"

    def get_context_data(self, **kwargs):
        context = super(PlaylistView, self).get_context_data(**kwargs)
        country = 'CH'
        context['tracks'] = Track.objects.get_available_tracks(country)
        context['playlist_url'] = 'spotify:trackset:Playlist:{}'.format(
            ','.join(track.uri for track in context['tracks'])
        )
        return context


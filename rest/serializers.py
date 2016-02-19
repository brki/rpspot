from urllib.parse import urlencode
from rest_framework import serializers
from trackmap import trackmap


class UnmatchedSongsSerializer(serializers.BaseSerializer):

    track_search = trackmap.TrackSearch()

    def to_representation(self, instance):

        artists = instance.artists.all()

        search_string = 'spotify {} {}'.format(
            instance.corrected_title or instance.title,
            " ".join([a.name for a in artists])
        )
        query_string = urlencode({'q': search_string})

        spotify_query, _, _, _ = self.track_search.spotify_query(instance)
        data = {
            'rp_song_id': instance.rp_song_id,
            'song_title': instance.title,
            'corrected_song_title': instance.corrected_title,
            'album': instance.album.title,
            'song_url': 'https://www.radioparadise.com/rp_2.php?#name=songinfo&song_id={}'.format(instance.rp_song_id),
            'artists': ', '.join(['[{}] {}'.format(a.id,  a.name) for a in artists]),
            'asin': 'http://www.amazon.com/exec/obidos/ASIN/{}'.format(instance.album.asin),
            'search_spotify': ' https://google.com/search?{}'.format(query_string),
            'query': spotify_query,
        }

        if hasattr(instance, 'last_played'):
            data['last_played'] = instance.last_played

        return data

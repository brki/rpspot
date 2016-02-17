from urllib.parse import urlencode
from rest_framework import serializers


class UnmatchedSongsSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):

        artists = instance.artists.all()

        search_string = 'spotify {} {}'.format(
            instance.title,
            " ".join([a.name for a in artists])
        )
        query_string = urlencode({'q': search_string})

        return {
            'rp_song_id': instance.rp_song_id,
            'song': instance.title,
            'album': instance.album.title,
            'song_url': 'https://www.radioparadise.com/rp_2.php?#name=songinfo&song_id={}'.format(instance.rp_song_id),
            'artists': ', '.join(['[{}] {}'.format(a.id,  a.name) for a in artists]),
            'asin': 'http://www.amazon.com/exec/obidos/ASIN/{}'.format(instance.album.asin),
            'search_spotify': ' https://google.com/search?{}'.format(query_string)
        }

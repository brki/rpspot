from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import IntegrityError
from rphistory.radioparadise import get_playlist_from_url, get_playlist_from_file, playlist_to_python
from rphistory.models import History, Song, Album, Artist
from logging import getLogger


log = getLogger(__name__)


class Command(BaseCommand):
    help = 'Loads new playlist history from radio paradise into database'

    def handle(self, *args, **options):

        latest_song = History.objects.all().order_by('-played_at').first()
        if latest_song:
            min_time = latest_song.played_at
        else:
            min_time = None

        latest_playlist = get_playlist_from_url()
        songs = playlist_to_python(latest_playlist, min_time=min_time)

        loaded = 0
        for song in songs:
            try:
                with transaction.atomic():
                    album_title = song['album'] or ''
                    if not album_title:
                        # TODO: try to get missing album title from asin
                        log.info(
                            "load_playlist: album title missing: [title: {}, asin: {}, release_year: {}]".format(
                                song['album'], song['album_asin'], song['album_release_year']))
                    album, _ = Album.objects.get_or_create(
                        asin=song['album_asin'],
                        defaults={'title': album_title, 'release_year': song['album_release_year']})
                    artist, _ = Artist.objects.get_or_create(name=song['artist'])
                    song_object, _ = Song.objects.get_or_create(
                        rp_song_id=song['id'], defaults={'title': song['title'], 'artist':artist, 'album': album})
                    History.objects.create(song=song_object, played_at=song['time'])
                    loaded += 1
            except IntegrityError as e:
                log.warn("load_playlist failed to process song {}: {}".format(song, e))
                continue

        self.stdout.write("Loaded {}/{} new song play histories".format(loaded, len(songs)))

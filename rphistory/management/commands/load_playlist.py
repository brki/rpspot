from django.core.management.base import BaseCommand, CommandError
from rphistory.radioparadise import get_playlist_from_url, playlist_to_python
from rphistory.models import History, Song, Album, Artist

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


        for song in songs:
            album = Album.objects.get_or_create(song['album_asin'], song['album'], song['album_release_year'])
            artist = Artist.objects.get_or_create(song['artist'])
            song_object = Song.objects.get_or_create(song['id'], song['title'], artist, album)
            History.objects.create(song=song_object, played_at=song['time'])

        self.stdout.write("Loaded {} new song play histories".format(len(songs)))

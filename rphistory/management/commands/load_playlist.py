from django.core.management.base import BaseCommand, CommandError
from rphistory.radioparadise import (
    get_playlist_from_url, get_playlist_from_file, playlist_to_python, save_songs_and_history)
from rphistory.models import History


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
        loaded = save_songs_and_history(songs)

        self.stdout.write("Loaded {}/{} new song play histories".format(loaded, len(songs)))

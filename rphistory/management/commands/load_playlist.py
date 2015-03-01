from django.core.management.base import BaseCommand, CommandError
from rphistory.radioparadise import (
    get_playlist_from_url, get_playlist_from_file, playlist_to_python, save_songs_and_history)
from rphistory.models import History
from rphistory.settings import RP_PLAYLIST_BASE


class Command(BaseCommand):
    help = 'Loads new playlist history from radio paradise into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--playlist',
            dest='playlist',
            default=None,
            help='Specify which playlist from https://www.radioparadise.com/xml to use (example: --playlist now_4.xml)')

    def handle(self, *args, **options):

        playlist_file = options['playlist']
        if playlist_file:
            url = RP_PLAYLIST_BASE + playlist_file
        else:
            url = None
        latest_song = History.objects.all().order_by('-played_at').first()
        if latest_song:
            min_time = latest_song.played_at
        else:
            min_time = None

        latest_playlist = get_playlist_from_url(url)
        if latest_playlist:
            songs = playlist_to_python(latest_playlist, min_time=min_time)
            loaded = save_songs_and_history(songs)
            self.stdout.write("Loaded {}/{} new song play histories".format(loaded, len(songs)))
        else:
            self.stdout.write("Playlist file unchanged, nothing to do.")

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from rphistory.models import History, Song, Album, Artist
from trackmap.models import Track, TrackAvailability, TrackSearchHistory
from trackmap.trackmap import TrackSearch, utc_now
from logging import getLogger

log = getLogger(__name__)


class Command(BaseCommand):
    help = 'Maps new Radio Paradise playlist songs to spotify tracks'

    def handle(self, *args, **options):

        now = utc_now()
        track_search = TrackSearch()
        new_songs = Song.objects.filter(search_history__isnull=True).select_related('album', 'artist')[:20]
        found_count = 0
        for song in new_songs:
            log.debug("Processing %s - %s", song.artist.name, song.title)
            perfect_matches, matches = track_search.get_market_track_availability(
                song, song.title, song.artist.name, song.album.title)
            # Prefer perfect matches.
            matches.update(perfect_matches)
            if matches:
                track_search.update_db_with_availibility(song, matches.values())
                found = True
                found_count += 1
            else:
                found = False

            TrackSearchHistory.objects.update_or_create(
                rp_song=song,
                defaults={'search_time': now, 'found': found}
            )
        self.stdout.write("Processed {} songs.  Matching Spotify tracks found for {} of these songs.".format(
            len(new_songs), found_count))

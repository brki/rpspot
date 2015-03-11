from django.core.management.base import BaseCommand
from django.db.models import Q
from rphistory.models import Song
from trackmap.models import TrackSearchHistory
from trackmap.trackmap import TrackSearch, utc_now
from logging import getLogger


log = getLogger(__name__)


class Command(BaseCommand):
    help = 'Maps new Radio Paradise playlist songs to Spotify tracks'

    def add_arguments(self, parser):
        parser.add_argument('--limit', dest='limit', nargs='?', type=int, default=0,
                            help='Only process <limit> new Radio Paradise songs')
        parser.add_argument('--failed', dest='failed', action='store_true', default=False,
                            help='Re-process songs for which no match was found')

    def handle(self, *args, **options):

        limit = options['limit']
        if options['failed']:
            filter = Q(search_history__found=False)
        else:
            filter = Q(search_history__isnull=True)

        new_songs = Song.objects.filter(filter).select_related('album', 'artist')
        if limit:
            new_songs = new_songs[:limit]

        now = utc_now()
        track_search = TrackSearch()
        found_count = 0
        for song in new_songs:
            matches, scores = track_search.find_matching_tracks(song)
            if matches:
                track_availabilities = track_search.create_tracks(song, matches, scores)
                track_search.update_db_with_availibility(song, track_availabilities)
                found = True
                found_count += 1
            else:
                found = False
            if not found:
                log.info("Not found: {} - {} (album: {}, asin: {})".format(
                    song.artist.name, song.title, song.album.title, song.album.asin))

            TrackSearchHistory.objects.update_or_create(
                rp_song=song,
                defaults={'search_time': now, 'found': found}
            )
        self.stdout.write("Processed {} songs.  Matching Spotify tracks found for {} of these songs.".format(
            len(new_songs), found_count))

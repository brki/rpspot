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
                            help='Only process <limit> new Radio Paradise songs.  Use a negative value to process the'
                                 ' newest songs (e.g. --limit -10 to process the latest 10 songs)')
        parser.add_argument('--failed', dest='failed', action='store_true', default=False,
                            help='Re-process songs for which no match was found')
        parser.add_argument('--force', dest='force', action='store_true', default=False,
                            help='(Re)process song, even if it has already been found (e.g. to find '
                                 'the updated list of countries where the song is available)')
        parser.add_argument('--songid', dest='rp_song_id', nargs='?', type=int, default=None,
                            help='Only process the given radio paradise song id (Song.rp_song_id value)')

    def handle(self, *args, **options):

        limit = options['limit']
        song_id = options['rp_song_id']
        filters = []

        if not options['force']:
            if options['failed']:
                filters.append(Q(search_history__found=False))
            else:
                filters.append(Q(search_history__isnull=True))

        if song_id is not None:
                filters.append(Q(rp_song_id=song_id))

        new_songs = Song.objects.filter(*filters).select_related('album').prefetch_related('artists')
        if limit:
            # If a negative value given, work back from the latest entries.
            if limit < 0:
                new_songs = new_songs.order_by('-search_history__id')
                limit *= -1
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
                # TODO: if not found, try harder: (also see TODOs in find_matching_tracks, might be better handled there)
                # * get album info from asin - if title is different, try with asin title
                # * if spotify album found matching asin title, but not the track: record in HandmappedTracks,
                #   it is probably a typo.

                found = False
            if not found:
                artists = ','.join([artist.name for artist in song.artists.all()])
                log.info("Not found: [{}] - {} (album: {}, asin: {})".format(
                    artists, song.title, song.album.title, song.album.asin))

            TrackSearchHistory.objects.update_or_create(
                rp_song=song,
                defaults={'search_time': now, 'found': found}
            )
        self.stdout.write("Processed {} songs.  Matching Spotify tracks found for {} of these songs.".format(
            len(new_songs), found_count))

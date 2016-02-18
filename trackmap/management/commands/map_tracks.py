from django.core.management.base import BaseCommand
from django.db.models import Q
from rphistory.models import Song
from trackmap.models import TrackSearchHistory, delete_references_to_rp_history_song
from trackmap.trackmap import TrackSearch, utc_now
from logging import getLogger


log = getLogger(__name__)


class Command(BaseCommand):
    help = 'Maps new Radio Paradise playlist songs to Spotify tracks'

    def add_arguments(self, parser):
        parser.add_argument('--limit', dest='limit', nargs='?', type=int, default=None,
                            help='Only process <limit> new Radio Paradise songs.  Use a negative value to process the'
                                 ' newest songs (e.g. --limit -10 to process the latest 10 songs)')
        parser.add_argument('--failed', dest='failed', action='store_true', default=False,
                            help='Re-process songs for which no match was found')
        parser.add_argument('--force', dest='force', action='store_true', default=False,
                            help='(Re)process song, even if it has already been found (e.g. to find '
                                 'the updated list of countries where the song is available)')
        parser.add_argument('--songid', dest='rp_song_id', nargs='?', type=int, default=None,
                            help='Only process the given radio paradise song id (Song.rp_song_id value)')
        parser.add_argument('--artistid', dest='artist_id', nargs='?', type=int, default=None,
                            help='Process all songs by the artist (Artist.id)')
        parser.add_argument('--delete-all-references-first', action='store_true', dest='delete_all_references',
                            default=False,
                            help='Delete all Trackmap references to song.  While processing a song '
                                 'with --force will remove all country-specific track availability '
                                 'mappings before creating the new mappings, it will not remove the track '
                                 'information or the album ' 'information.  Using this option will remove these '
                                 'references, too ' '(album information will not be deleted unless no other tracks '
                                 'refer to the album).  Note that it is necessary to also use the --force argument '
                                 'if you want to reprocess the song(s) even if they have already been mapped.')
        parser.add_argument('--slice', dest='slice_string', nargs='?', type=str, default=None,
                            help='Slice the resulting Song queryset, e.g. --slice 10:20 would only process items '
                                 '10 - 19 of the queryset that selects the songs to process')

    def handle(self, *args, **options):

        limit = options['limit']
        slice_string = options['slice_string']
        song_id = options['rp_song_id']
        artist_id = options['artist_id']
        delete_all_references = options['delete_all_references']
        force = options['force']

        if limit is not None and slice_string is not None:
            raise ValueError("Only one of --limit or --slice can be used.")

        slice_tuple = None
        order_by = 'search_history__id'
        if slice_string is not None:
            try:
                lower_string, higher_string = slice_string.split(':')
                lower = int(lower_string)
                higher = int(higher_string)
            except:
                raise ValueError("Value provided for --slice could not be parsed, expecting something like 10:15")

            if lower >= higher:
                raise ValueError("--slice value must be in form of <lower_number>:<higher_number>, for example 10:15")

            if lower < 0:
                raise ValueError("--slice does not except negative numbers")

            slice_tuple = (lower, higher)
        elif limit is not None:
            # If a negative value given, work back from the latest entries.
            if limit < 0:
                order_by = '-' + order_by
                slice_tuple = (None, -1 * limit)
            else:
                slice_tuple = (None, limit)

        filters = []
        if not force:
            if options['failed']:
                filters.append(Q(search_history__found=False))
            else:
                filters.append(Q(search_history__isnull=True))

        if song_id is not None:
                filters.append(Q(rp_song_id=song_id))

        if artist_id is not None:
            filters.append(Q(artists__id=artist_id))

        new_songs = Song.objects.filter(*filters).select_related('album').prefetch_related('artists').order_by(order_by)

        if slice_tuple is not None:
            start, stop = slice_tuple
            new_songs = new_songs[start:stop]

        now = utc_now()
        track_search = TrackSearch()
        found_count = 0
        for song in new_songs:
            if delete_all_references:
                delete_references_to_rp_history_song(song.id)

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
                    artists, song.corrected_title or song.title, song.album.title, song.album.asin))

            TrackSearchHistory.objects.update_or_create(
                rp_song=song,
                defaults={'search_time': now, 'found': found}
            )

        self.stdout.write("Processed {} songs.  Matching Spotify tracks found for {} of these songs.".format(
            len(new_songs), found_count))

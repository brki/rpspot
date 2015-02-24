from collections import namedtuple
import logging
import re
from operator import itemgetter
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from spotify.spotify import spotify
from trackmap.models import Album, Track, TrackAvailability
import unicodedata


AlbumInfo = namedtuple('AlbumInfo', 'id title year img_small img_medium img_large match_score')
ArtistInfo = namedtuple('ArtistInfo', 'id name multiple match_score')
TrackInfo = namedtuple('ArtistInfo', 'id title match_score')
TrackArtistAlbum = namedtuple('TrackArtistAlbum', 'track_info artist_info album_info')


log = logging.getLogger(__name__)


def utc_now():
    return timezone.now().replace(tzinfo=timezone.utc)


def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not unicodedata.combining(c)])

def chunks(l, n):
    """
    Breaks a single list into several lists of size n.
    :param list l: list to break into chunks
    :param int n: number of elements that each chunk should have
    :return: list of lists
    """
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]

class TrackSearch(object):

    rp_to_spotify_artist_map = {
        'Bob Marley': 'Bob Marley & The Wailers',
        'The English Beat': 'The Beat',
    }

    def __init__(self, query_limit=40, max_items_to_process=200):
        self.spotify = spotify()
        self.query_limit = query_limit
        self.max_items_to_process = max_items_to_process
        self.strip_non_words_pattern = re.compile('[\W_]+', re.UNICODE)

    def find_matching_tracks(self, song):
        """
        Gets the matching tracks that can be played per country.

        :param song: rphistory.Song object
        :param track_title: title to search
        :param artist_name: artist to search
        :param album_title: album to search
        :param album_year: album release year to search
        :return: tuple: perfect_matches_dict, almost_matches_dict
        """
        query = self.build_query(song.title, artist_name=song.artist.name)
        results = self.get_query_results(query)
        self.add_full_album_info(results)
        best_matches = {}
        matches_score = {}
        artist_name = self.map_artist_name(song.artist.name)
        for item in results:
            track_info = self.extract_track_info(song.title, item)
            artist_info = self.extract_artist_info(artist_name, item['artists'])
            album_info = self.extract_album_info(song.album.title, song.album.release_year, item)
            if track_info is None or artist_info is None:
                # If the artist or track was not found, no need to process this item.
                continue

            score = sum(info.match_score for info in [track_info, artist_info, album_info])
            for country in item['available_markets']:
                previous_score = matches_score.get(country, -1)
                if score > previous_score:
                    matches_score[country] = score
                    best_matches[country] = TrackArtistAlbum(
                        track_info=track_info, artist_info=artist_info, album_info=album_info
                    )
        return best_matches

    def create_tracks(self, song, market_tracks):
        """
        Create the tracks and artist objects, and collects the per-market TrackAvailability objects.

        :param song: rphistory.Song object
        :param country_tracks: map of country name string => TrackArtistAlbum namedtumple
        :return: list of TrackAvailability objects
        """
        availabilities = []
        track_cache = {}
        for country, info in market_tracks.items():
            spotify_id = info.track_info.id
            track = track_cache.get(spotify_id, None)
            if not track:
                try:
                    track = self.get_or_create_track(info.track_info, info.artist_info, info.album_info)
                    track_cache[spotify_id] = track
                except IntegrityError as e:
                    log.warn("Problem creating track for rp song {}: {}".format(song.rp_song_id, e))
                    continue
            track_availability = TrackAvailability(track=track, rp_song=song, country=country)
            track_availability.full_clean(validate_unique=False)
            availabilities.append(track_availability)
        return availabilities

    @transaction.atomic
    def update_db_with_availibility(self, song, track_availabilities):
        """
        Atomically deletes previous track availability data and inserts new data

        :param song: rphistory.Song object
        :param track_availabilities: array of TrackAvailability objects
        :return:
        """
        TrackAvailability.objects.filter(rp_song=song).delete()
        if track_availabilities:
            TrackAvailability.objects.bulk_create(track_availabilities)

    def build_query(self, track_title, artist_name=None, album_title=None):
        """
        Builds a query based on the passed values.

        :param track_title:
        :param artist_name:
        :param album_title:
        :return: query string
        """
        q = ['track:"{}"'.format(track_title)]
        if artist_name:
            q.append('artist:"{}"'.format(artist_name))
        if album_title:
            q.append('album:"{}"'.format(album_title))
        return ' '.join(q)

    def get_query_results(self, query, limit=None, max_items=None):
        """
        Gets as many query results as specified; handles Spotify's paging API.

        Note that max_items is not strict, all results from each page of results are added.
        E.g. with limit=5, max_items=7, you will get two full pages of results (10 items) if there are
        that many possible results.

        :param query: query dict like the one returned from build_query()
        :param limit: limit-per-page; defaults to self.query_limit
        :param max_items: max tracks to accumulate before returning.
        :return: array of track items
        """
        limit = limit or self.query_limit
        max_items = max_items or self.max_items_to_process
        all_items = []
        total = 0
        offset = 0
        keep_going = True
        while keep_going:
            results = self.spotify.search(q=query, type='track', limit=limit, offset=offset)
            items = results['tracks']['items']
            count = len(items)
            if count:
                all_items += items
                total += count
                offset += count
            keep_going = results['tracks']['next'] and total < max_items
            if total > max_items:
                log.warn("The query '{}' returned more than max_items={} results!".format(query, max_items))
        return all_items

    def add_full_album_info(self, items):
        """
        Adds full album info for the retrieved results, and adds a ``release_year`` element to the full album info.

        Modifies passed items.

        :param items: track query result items
        :return: None
        """
        # Spotify limits getting multiple albums in one query to 20 albums.
        max_ids = 20

        album_ids = {item['album']['id'] for item in items}
        id_lists = chunks(list(album_ids), max_ids)

        album_info = {}
        for id_list in id_lists:
            for album in self.spotify.albums(id_list)['albums']:
                album['release_year'] = album['release_date'].split('-')[0]
                album_info[album['id']] = album

        for item in items:
            item['album'] = album_info[item['album']['id']]

    def simplified_text(self, string):
        string = string.lower().replace(' & ', ' and ').replace(' + ', ' and ')
        return remove_accents(self.strip_non_words_pattern.sub('', string))

    def extract_artist_info(self, artist, artist_list):
        """
        Find a matching artist. There may be many artists, but we don't care, we just search for ``artist``.

        Spotify's search api doesn't allow for requiring exact matches, so we try here to do a reasonably
        good job of detecting a matching artist name.

        :param artist: string
        :param artist_list: array of spotify API album results
        :return: ArtistInfo
        """
        artist_simple = self.simplified_text(artist)
        artist_alternate = 'the' + artist_simple
        multiple = len(artist_list) > 1
        for a in artist_list:
            a_simple = self.simplified_text(a['name'])
            a_alternate = 'the' + a_simple
            if len({artist_simple, artist_alternate, a_simple, a_alternate}) < 4:
                # At least one of the pairs matched.
                match_score = int(artist_simple == a_simple)
                return ArtistInfo(id=a['id'], name=a['name'], multiple=multiple, match_score=match_score)
        else:
            message = "Artist '{}' not found in list: {}".format(
                artist, [a['name'] for a in artist_list]
            )
            log.debug(message)
        return None

    def extract_album_info(self, expected_album, expected_year, item):
        album = item['album']
        expected_simple = self.simplified_text(expected_album)
        item_simple = self.simplified_text(album['name'])
        item_year = int(album['release_year'])
        match_score = int(item_simple == expected_simple) + int(expected_year == item_year)
        img_small = None
        img_med = None
        img_large = None
        images = sorted(album['images'], key=itemgetter('height'))
        count = len(images)
        if count == 1:
            img_small = img_med = img_large = images[0]['url']
        elif count == 2:
            img_small = images[0]['url']
            img_med = img_large = images[1]['url']
        elif count > 2:
            img_small = images[0]['url']
            img_med = images[-2]['url']
            img_large = images[-1]['url']
        return AlbumInfo(
            id=album['id'], title=album['name'], year=item_year,
            img_small=img_small, img_medium=img_med, img_large=img_large,
            match_score=match_score
        )

    def extract_track_info(self, track_title, item):
        track_simple = self.simplified_text(track_title)
        item_track_simple = self.simplified_text(item['name'])

        track_match = track_simple == item_track_simple
        if not track_match:
            # Accept things like "song name 2004 remaster":
            regex = r"^" + track_simple + r"(\d{4})?((digital)?(remaster(ed)?))?"
            track_match = re.match(regex, item_track_simple)
        if track_match:
            return TrackInfo(id=item['id'], title=item['name'], match_score=1)
        else:
            message = "Expected track: {}, found track: {}".format(track_title, item['name'])
            log.debug(message)
        return None

    @transaction.atomic
    def get_or_create_track(self, track_info, artist_info, album_info):
        """
        Gets or creates the track, also getting or creating the album.

        :param TrackInfo track_info:
        :param ArtistInfo artist_info:
        :param AlbumInfo album_info:
        :return: Track
        """
        album_defaults = {
            'title': album_info.title,
            'img_small_url': album_info.img_small,
            'img_medium_url': album_info.img_medium,
            'img_large_url': album_info.img_large,
            }
        album_obj = self.get_or_create_and_update_if_needed(Album, {'spotify_id': album_info.id}, album_defaults)

        track_defaults = {
            'title': track_info.title,
            'album': album_obj,
            'artist': artist_info.name,
            'artist_id': artist_info.id,
            'many_artists': artist_info.multiple,
            }
        track_obj = self.get_or_create_and_update_if_needed(Track, {'spotify_id': track_info.id}, track_defaults)
        return track_obj

    def get_or_create_and_update_if_needed(self, model, kwargs, defaults):
        """
        Similar to Django's get_or_create / update_or_create, but only updates if something changed.

        :param model: model class
        :param kwargs: dict of field/value pairs used to identify an existing object
        :param defaults: dict of field/value paris that will be used for other, non-identifying fields
        :return:
        """
        #TODO: should clean before creating, too.
        obj, created = model.objects.get_or_create(defaults=defaults, **kwargs)

        # Save back to DB if any info has changed.
        if not created:
            clean_exclude = list(kwargs)
            changed = False
            for k, v in defaults.items():
                if getattr(obj, k) != v:
                    changed = True
                    setattr(obj, k, v)
                else:
                    clean_exclude.append(k)
            if changed:
                obj.full_clean(exclude=clean_exclude, validate_unique=False)
        return obj

    def map_artist_name(self, artist_name):
        """
        Replace Radio Paradise name with Spotify name for some artists that are named differently by the two services.
        :param artist_name:
        :return: string
        """
        #TODO: should these be managed in the DB?
        return self.rp_to_spotify_artist_map.get(artist_name, artist_name)

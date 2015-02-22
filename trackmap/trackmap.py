from collections import namedtuple
import logging
import re
from operator import itemgetter
from django.db import transaction
from django.utils import timezone
from spotify.spotify import spotify
from trackmap.models import Album, Track, TrackAvailability
import unicodedata


AlbumInfo = namedtuple('AlbumInfo', 'id title img_small img_medium img_large exact_match')
ArtistInfo = namedtuple('ArtistInfo', 'id name multiple')
TrackInfo = namedtuple('ArtistInfo', 'id title')


log = logging.getLogger(__name__)


def utc_now():
    return timezone.now().replace(tzinfo=timezone.utc)


def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not unicodedata.combining(c)])


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

    def get_market_track_availability(self, song, track_title, artist_name, album_title):
        """
        Gets the matching tracks that can be played per country.

        :param song: rphistory.Song object
        :param track_title: title to search
        :param artist_name: artist to search
        :param album_title: album to search
        :return: tuple: perfect_matches_dict, almost_matches_dict
        """
        query = self.build_query(track_title, artist_name=artist_name)
        results = self.get_query_results(query)
        perfect_matches = {}
        almost_matches = {}
        for item in results:
            track_info = self.extract_track_info(track_title, item)
            artist_info = self.extract_artist_info(artist_name, item['artists'])
            album_info = self.extract_album_info(album_title, item)
            if track_info is None or artist_info is None:
                # If the artist or track was not found, no need to process this item.
                continue

            track = self.get_or_create_track(track_info, artist_info, album_info)

            #TODO: Base this on a score, not a boolean (e.g. if track and artist but not album match perfectly, score=2)
            #      Replace items in almost_matches if score is higher than previous entry.

            perfect_match = self.is_perfect_match(
                track_title, artist_name, album_title, track_info, artist_info, album_info)

            matches = perfect_matches if perfect_match else almost_matches
            for country in item['available_markets']:
                if country not in matches:
                    availability = TrackAvailability(track=track, rp_song=song, country=country)
                    availability.full_clean(validate_unique=False)
                    matches[country] = availability

        return perfect_matches, almost_matches

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
                return ArtistInfo(id=a['id'], name=a['name'], multiple=multiple)
        else:
            message = "Artist '{}' not found in list: {}".format(
                artist, [a['name'] for a in artist_list]
            )
            log.debug(message)
        return None

    def extract_album_info(self, expected_album, item):
        album = item['album']
        expected_simple = self.simplified_text(expected_album)
        item_simple = self.simplified_text(album['name'])
        exact_match = expected_simple == item_simple
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
            id=album['id'], title=album['name'],
            img_small=img_small, img_medium=img_med, img_large=img_large,
            exact_match=exact_match
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
            return TrackInfo(id=item['id'], title=item['name'])
        else:
            message = "Expected track: {}, found track: {}".format(track_title, item['name'])
            log.debug(message)
        return None

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

    def is_perfect_match(self, track_title, artist_name, album_title, track_info, artist_info, album_info):
        """
        Checks if it is a perfect match, or if one or more of the attributes don't match.

        :param string track_title:
        :param string artist_name:
        :param string album_title:
        :param TrackInfo track_info:
        :param ArtistInfo artist_info:
        :param AlbumInfo album_info:
        :return: boolean
        """
        return (
            track_info.title.lower() == track_title.lower()
            and album_info.title.lower() == album_title.lower()
            and artist_info.name.lower() == artist_name.lower()
        )

    def map_artist_name(self, artist_name):
        """
        Replace Radio Paradise name with Spotify name for some artists that are named differently by the two services.
        :param artist_name:
        :return: string
        """
        #TODO: should these be managed in the DB?
        return self.rp_to_spotify_artist_map.get(artist_name, artist_name)

from collections import namedtuple
from operator import itemgetter
from django.db import transaction
from django.utils import timezone
from spotify.spotify import spotify
from trackmap.models import Track, TrackAvailability


TrackInfo = namedtuple('TrackInfo', 'uri title img_small img_medium img_large')

def utc_now():
    return timezone.now().replace(tzinfo=timezone.utc)


class TrackSearch(object):

    def __init__(self, query_limit=40, max_items_to_process=200):
        self.spotify = spotify()
        self.query_limit=query_limit
        self.max_items_to_process=max_items_to_process

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
            track = self.get_or_create_track(item, track_title, artist_name, album_title)
            perfect_match = self.is_perfect_match(track, track_title, artist_name, album_title)
            matches = perfect_matches if perfect_match else almost_matches
            for country in item['available_markets']:
                if not country in matches:
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
        Gets as many query results as specified; handles Spotifies paging API.

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
        return all_items

    def extract_artist_info(self, artist, artist_list):
        for a in artist_list:
            if a['name'].lower() == artist.lower():
                return a['name'], a['uri'], len(artist_list) > 1
                #TODO: handle inexact matches

    def extract_album_info(self, expected_album, album):
        return album['name'], album['uri'], album['name'].lower() == expected_album.lower()

    def extract_track_info(self, item):
        #TODO: get these values from the album.images list:

        img_small = None
        img_med = None
        img_large = None
        images = sorted(item['album']['images'], key=itemgetter('height'))
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
        return TrackInfo(
            uri=item['uri'], title=item['name'], img_small=img_small, img_medium=img_med, img_large=img_large)

    def get_or_create_track(self, item, song, artist, album):
        artist_name, artist_uri, many_artists = self.extract_artist_info(artist, item['artists'])
        album_name, album_uri, same_album = self.extract_album_info(album, item['album'])
        track_info = self.extract_track_info(item)

        defaults = {
            'title': track_info.title,
            'album': album_name,
            'album_uri': album_uri,
            'artist': artist_name,
            'artist_uri': artist_uri,
            'many_artists': many_artists,
            'img_small_url': track_info.img_small,
            'img_medium_url': track_info.img_medium,
            'img_large_url': track_info.img_large,
            }
        obj, created = Track.objects.get_or_create(uri = track_info.uri, defaults=defaults)

        # Save back to DB if any info has changed.
        if not created:
            clean_exclude = ['uri']
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

    def is_perfect_match(self, track, track_title, artist_name, album_title):
        """
        Checks if it is a perfect match, or if one or more of the attributes don't match.

        :param track: Track object
        :param track_title:
        :param artist_name:
        :param album_title:
        :return: boolean
        """
        return (track.title.lower == track_title.lower()
                and track.artist() == artist_name.lower()
                and track.album() == album_title.lower()
        )


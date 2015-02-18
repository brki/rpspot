from base64 import b64encode
from collections import namedtuple
from django.conf import settings
from django.core.cache import caches
from trackmap.models import Track, TrackAvailability, TrackSearchHistory
import requests
import spotipy

CLIENT_CREDENTIALS_CACHE_KEY='spotify_client_credentials'
CLIENT_CREDENTIALS_URL='https://accounts.spotify.com/api/token'

TrackResult = namedtuple('TrackResult', 'uri album_match available_markets')
#TODO: rename me:
TrackInfo = namedtuple('TrackInfo', 'uri title img_small img_medium img_large')

def spotify():
    return spotipy.Spotify(auth=client_credentials_token())

def spotify_cache():
    return caches[settings.SPOTIFY_CACHE]

def client_credentials_token():
    cache = spotify_cache()
    token = cache.get(CLIENT_CREDENTIALS_CACHE_KEY)
    if not token:
        token, _, expires = fetch_new_client_credentials_token()
        cache.set(CLIENT_CREDENTIALS_CACHE_KEY, token, expires - 60)
    return token

def fetch_new_client_credentials_token():
    data = {'grant_type': 'client_credentials'}

    auth_token = b64encode('{}:{}'.format(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET).encode('ascii'))
    headers = {'Authorization': b'Basic ' + auth_token}
    r = requests.post(CLIENT_CREDENTIALS_URL, data=data, headers=headers)
    r.raise_for_status()
    result = r.json()
    return result['access_token'], result['token_type'], result['expires_in']


def find_track(track, artist=None, album=None, country_code=None):
    """
    Find a spotify track uri for the single best-matching track.

    TrackResult.album_match is True if the track was found on the requested album

    :param track: track title (optional)
    :param artist: artist name (optional)
    :param album: album title (optional)
    :param country_code: uppercase two-letter country code (optional)
    :return: TrackResult if a track found, None otherwise
    """

    def track_match(track, track_value):
        return track == track_value

    def artist_match(artist, artists):
        if artist is None:
            return True
        for a in artists:
            if a['name'].lower() == artist.lower():
                return True
        return False

    def album_match(album_name, album):
        if album_name is None:
            return True
        return album_name.lower() == album['name'].lower()


    kwargs = {
        'q': ' '.join(q),
        'type': 'track',
    }
    if country_code:
        kwargs['market'] = country_code

    s = spotify()
    results = s.search(**kwargs)
    matches = []
    if results['tracks']['total'] >= 1:
        for item in results['tracks']['items']:
            if artist_match(artist, item['artists']) and track_match(track, item['name']):
                result = TrackResult(item['uri'], album_match(album, item['album']), item['available_markets'])
                if result.album_match:
                    return result
                else:
                    matches.append(result)
    if matches:
        # If no match at the album level, return the first artist + track match found
        return matches[0]

    return None

#TODO: move me to trackmap
class TrackSearch(object):

    def __init__(self):
        self.spotify = spotify()

    def extract_artist_info(self, artist, artist_list):
        for a in artist_list:
            if a['name'].lower() == artist.lower():
                return a['name'], a['uri'], len(artist_list) > 1
        #TODO: handle inexact matches

    def extract_album_info(self, expected_album, album):
        return album['name'], album['uri'], album['name'].lower() == expected_album.lower()

    def extract_track_info(self, item):
        #TODO: get these values:
        img_small = None
        img_med = None
        img_large = None
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
        obj, created =  Track.objects.get_or_create(uri = track_info.uri, defaults=defaults)

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

    def is_perfect_match(self, track_info, track_title, artist_name, album_title):
        return (track_info.title.lower == track_title.lower()
                and track_info.artist() == artist_name.lower()
                and track_info.album() == album_title.lower()
        )

    def get_market_track_info(self, track_title, artist_name, album_title):
        query = self.build_query(track_title, artist_name=artist_name)
        results = self.spotify.search(q=query, type='track')
        perfect_matches = {}
        almost_matches = {}
        for item in results['tracks']['items']:
            track = self.get_or_create_track(item, track_title, artist_name, album_title)
            perfect_match = self.is_perfect_match(track_info, track_title, artist_name, album_title)
            matches = perfect_matches if perfect_match else almost_matches
            for country in item['markets']:
                if not country in matches:
                    matches[country] = TrackAvailability(track=track, song=song, country=country)

        #TODO: update_results_in_db
    def build_query(self, track_title, artist_name=None, album_title=None):
        q = ['track:"{}"'.format(track_title)]
        if artist_name:
            q.append('artist:"{}"'.format(artist_name))
        if album_title:
            q.append('album:"{}"'.format(album_title))



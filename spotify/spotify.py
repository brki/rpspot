from base64 import b64encode
from collections import namedtuple
from django.conf import settings
from django.core.cache import caches
import requests
import spotipy


CLIENT_CREDENTIALS_CACHE_KEY = 'spotify_client_credentials'
CLIENT_CREDENTIALS_URL = 'https://accounts.spotify.com/api/token'

TrackResult = namedtuple('TrackResult', 'id album_match available_markets')


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


def find_track(track, artist=None, album=None):
    """
    Find a spotify track id for the single best-matching track.

    TrackResult.album_match is True if the track was found on the requested album

    :param track: track title (optional)
    :param artist: artist name (optional)
    :param album: album title (optional)
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

    q = ['track:"{}"'.format(track)]
    if artist:
        q.append('artist:"{}"'.format(artist))

    kwargs = {
        'q': ' '.join(q),
        'type': 'track',
    }

    s = spotify()
    results = s.search(**kwargs)
    matches = []
    if results['tracks']['total'] >= 1:
        for item in results['tracks']['items']:
            if artist_match(artist, item['artists']) and track_match(track, item['name']):
                result = TrackResult(item['id'], album_match(album, item['album']), item['available_markets'])
                if result.album_match:
                    return result
                else:
                    matches.append(result)
    if matches:
        # If no match at the album level, return the first artist + track match found
        return matches[0]

    return None

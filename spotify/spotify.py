from base64 import b64encode
from django.conf import settings
from django.core.cache import caches
import requests
import spotipy

CLIENT_CREDENTIALS_CACHE_KEY='spotify_client_credentials'
CLIENT_CREDENTIALS_URL='https://accounts.spotify.com/api/token'

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


#spotify = spotipy.Spotify()

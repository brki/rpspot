from unittest import TestCase
import spotipy
from spotify.spotify import spotify_cache, client_credentials_token, find_track


class ClientCredentialsToken(TestCase):

    def setUp(self):
        spotify_cache().clear()

    def test_token_cached(self):
        token = client_credentials_token()
        self.assertIsNotNone(token)
        token2 = client_credentials_token()
        self.assertEqual(token, token2)


class SearchTrack(TestCase):

    def test_search_track(self):
        s = spotipy.Spotify(auth=client_credentials_token())
        result = s.search(q='track:Rainy artist:"Bob Dylan"', type='track')
        self.assertGreater(result['tracks']['total'], 1)

    def test_find_track(self):
        result = find_track(
            artist='Shriekback', track='All Lined Up', album='Natural History')
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.id)
        self.assertFalse(result.album_match)
        self.assertIn('CH', result.available_markets)
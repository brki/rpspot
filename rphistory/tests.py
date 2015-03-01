from django.test import TestCase
from rphistory.radioparadise import rphistory_cache, get_playlist_from_url
from rphistory.settings import RP_PLAYLIST_BASE

from rphistory.radioparadise import get_info_from_asin


class AsinFetch(TestCase):
    def test_album_title_from_asin(self):
        asin = 'B0000062FJ'
        expected_title = 'Santana'
        info = get_info_from_asin(asin)
        self.assertIsNotNone(info)
        self.assertEqual(expected_title, info.title)


class PlaylistFetch(TestCase):
    def tearDown(self):
        rphistory_cache().clear()

    def test_etag_caching(self):
        url = RP_PLAYLIST_BASE + 'now.xml'

        cache = rphistory_cache()
        cache.clear()

        # This could fail if a new now.xml is put in place between requests ...
        # Perhaps the url fetching should be mocked somehow.
        data = get_playlist_from_url(url)
        self.assertIsNotNone(data)
        data = get_playlist_from_url(url)
        self.assertIsNone(data)
        cache.clear()
        data = get_playlist_from_url(url)
        self.assertIsNotNone(data)

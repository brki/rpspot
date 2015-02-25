from django.test import TestCase

from rphistory.radioparadise import get_info_from_asin

class AsinFetch(TestCase):
    def test_album_title_from_asin(self):
        asin = 'B0000062FJ'
        expected_title = 'Santana'
        info = get_info_from_asin(asin)
        self.assertIsNotNone(info)
        self.assertEqual(expected_title, info.title)

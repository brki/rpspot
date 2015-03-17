from unittest import TestCase

from trackmap.views import get_utc_start_time

class Time(TestCase):
    def test_utc_time_from_naive_time(self):
        pst = 'America/Los_Angeles'
        naive = '2015-03-11 12:00'
        utc = get_utc_start_time(naive, pst)
        self.assertEqual((2015, 3, 11, 19, 0), (utc.year, utc.month, utc.day, utc.hour, utc.minute))

    def test_utc_time_from_aware_time(self):
        pst = 'America/Los_Angeles'
        aware = '2015-03-11 10:00 -3:00'
        utc = get_utc_start_time(aware, pst)
        self.assertEqual((2015, 3, 11, 13, 0), (utc.year, utc.month, utc.day, utc.hour, utc.minute))




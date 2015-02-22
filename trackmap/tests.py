from unittest import TestCase
from rphistory.models import Song, Artist, Album
from trackmap.trackmap import TrackSearch


#TODO:
# * test perfect match returns real perfect match (subject to breakage if spotify changes content)
# class BethOrton(TestCase):
#
#     def test_she_cries_your_name(self):
#         t = TrackSearch()
#
#         album = Album.objects.create(title="Trailer Park", asin="B000003RSF", release_year=1996)
#         artist = Artist.objects.create(name="Beth Orton")
#         song = Song.objects.create(title="She Cries Your Name", rp_song_id=31550, artist=artist, album=album)
#         artist_name = t.map_artist_name(song.artist.name)
#         perfect_matches, matches = t.get_market_track_availability(song, song.title, artist_name, song.album.title)
#         matches.update(perfect_matches)
#         self.assertEqual(matches['CH'].)
#         a=1


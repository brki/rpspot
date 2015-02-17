from django.db import models
from rphistory.models import Song

class Track(models.Model):
    spotify_track_id = models.CharField(max_length=120)

class TrackMap(models.Model):
    track = models.ForeignKey(Track)
    rp_song = models.ForeignKey(Song)
    country_code = models.CharField(max_length=2, null=False)
    album_match = models.BooleanField(default=False)
    modified = models.DateTimeField(auto_now=True, auto_now_add=True, null=False)

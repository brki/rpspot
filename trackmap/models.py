from django.db import models
from rphistory.models import Song

class Track(models.Model):
    uri = models.CharField(max_length=120, help_text="A spotify track uri", unique=True)
    title = models.CharField(max_length=255, blank=False, help_text="Track title")
    album = models.CharField(max_length=255, blank=False, help_text="Album title")
    album_uri = models.CharField(max_length=120, help_text="A spotify album uri")
    artist = models.CharField(max_length=255, blank=False, help_text="Primary artist name")
    artist_uri = models.CharField(max_length=120, help_text="A spotify artist uri")
    many_artists = models.BooleanField(default=False)
    img_small_url = models.URLField(null=True)
    img_medium_url = models.URLField(null=True)
    img_large_url = models.URLField(null=True)


class TrackAvailability(models.Model):
    track = models.ForeignKey(Track)
    rp_song = models.ForeignKey(Song, related_name="available_tracks")
    country = models.CharField(max_length=2)

    class Meta:
        unique_together = (('track', 'rp_song', 'country'))


class TrackSearchHistory(models.Model):
    rp_song = models.OneToOneField(Song, related_name="search_history")
    search_time = models.DateTimeField(null=False)
    found = models.BooleanField(default=False)
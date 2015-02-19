from django.db import models
from rphistory.models import Song


class Album(models.Model):
    uri = models.CharField(max_length=120, unique=True, help_text="A spotify album uri")
    title = models.CharField(max_length=255, blank=False, help_text="Album title")
    img_small_url = models.URLField(null=True)
    img_medium_url = models.URLField(null=True)
    img_large_url = models.URLField(null=True)


class Track(models.Model):
    uri = models.CharField(max_length=120, help_text="A spotify track uri", unique=True)
    title = models.CharField(max_length=255, blank=False, help_text="Track title")
    album = models.ForeignKey(Album)
    artist = models.CharField(max_length=255, blank=False, help_text="Primary artist name")
    artist_uri = models.CharField(max_length=120, help_text="A spotify artist uri")
    many_artists = models.BooleanField(default=False)


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
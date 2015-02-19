from django.db import models
from rphistory.models import Song, History


class Album(models.Model):
    uri = models.CharField(max_length=120, unique=True, help_text="A spotify album uri")
    title = models.CharField(max_length=255, blank=False, help_text="Album title")
    img_small_url = models.URLField(null=True)
    img_medium_url = models.URLField(null=True)
    img_large_url = models.URLField(null=True)


class TrackManager(models.Manager):
    def get_available_tracks(self, country, start_time=None, limit=15):

        params = {'country': country, 'limit': limit}
        if start_time:
            order_direction = 'ASC'
            date_clause = 'AND h.played at >= %(start_time)s'
            params['start_time'] = start_time
        else:
            order_direction = 'DESC'
            date_clause = ''

        sql = '''
            SELECT t.id, replace(t.uri, 'spotify:track:', '') AS uri, t.title, t.artist,
                   a.title AS album_title, a.img_small_url, h.played_at
              FROM {track} t
              JOIN {album} a ON t.album_id = a.id
              JOIN {track_availability} ta ON t.id = ta.track_id
              JOIN {history} h ON ta.rp_song_id = h.song_id
             WHERE ta.country = %(country)s
                   {date_clause}
          ORDER BY h.played_at {order_direction}
             LIMIT %(limit)s
          '''.format(
            track=Track._meta.db_table,
            album=Album._meta.db_table,
            track_availability=TrackAvailability._meta.db_table,
            history=History._meta.db_table,
            date_clause=date_clause,
            order_direction=order_direction
        )

        qs = self.raw(sql, params)
        if not start_time:
            qs = list(qs)
            qs.reverse()
        return qs

class Track(models.Model):
    uri = models.CharField(max_length=120, help_text="A spotify track uri", unique=True)
    title = models.CharField(max_length=255, blank=False, help_text="Track title")
    album = models.ForeignKey(Album)
    artist = models.CharField(max_length=255, blank=False, help_text="Primary artist name")
    artist_uri = models.CharField(max_length=120, help_text="A spotify artist uri")
    many_artists = models.BooleanField(default=False)
    objects = TrackManager()


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
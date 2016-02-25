from logging import getLogger, DEBUG
from django.db import models
from django.apps import apps

from trackmap import trackmap_cache


log = getLogger(__name__)


class Album(models.Model):
    spotify_id = models.CharField(max_length=120, unique=True, help_text="A spotify album id")
    title = models.CharField(max_length=255, blank=False, help_text="Album title")
    img_small_url = models.URLField(null=True)
    img_medium_url = models.URLField(null=True)
    img_large_url = models.URLField(null=True)

    def __str__(self):
        return "<Album>: {} (spotify_id: {}) (id: {})".format(self.title, self.spotify_id, self.id)


class TrackManager(models.Manager):
    def get_available_tracks(self, country, start_time=None, limit=15):

        History = apps.get_model('rphistory', 'History')
        params = {'country': country, 'limit': limit}
        if start_time:
            order_direction = 'ASC'
            date_clause = 'AND h.played_at >= %(start_time)s'
            params['start_time'] = start_time
        else:
            order_direction = 'DESC'
            date_clause = ''

        sql = '''
            SELECT t.id, t.spotify_id, t.title, t.artist,
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
    spotify_id = models.CharField(max_length=120, help_text="A spotify track id", unique=True)
    title = models.CharField(max_length=255, blank=False, help_text="Track title")
    album = models.ForeignKey(Album)
    artist = models.CharField(max_length=255, blank=False, help_text="Primary artist name")
    artist_id = models.CharField(max_length=120, help_text="A spotify artist id")
    many_artists = models.BooleanField(default=False)
    objects = TrackManager()

    def __str__(self):
        return "<Track>: {} (artist: {}) (spotify_id: {}) (id: {})".format(
            self.title, self.artist, self.spotify_id, self.id)


class TrackAvailabilityManager(models.Manager):
    def all_markets(self, force_cache_refresh=False):
        cache = trackmap_cache()
        cache_key = 'track_availability_countries'
        if not force_cache_refresh:
            countries = cache.get(cache_key)
            if countries:
                return countries

        countries = self.values_list('country', flat=True).distinct('country').order_by('country')
        cache.set(cache_key, countries, 60*60*24)
        return countries


class TrackAvailability(models.Model):
    track = models.ForeignKey(Track)
    rp_song = models.ForeignKey('rphistory.Song', related_name="available_tracks")
    country = models.CharField(max_length=2, db_index=True)
    score = models.IntegerField(default=0)
    objects = TrackAvailabilityManager()

    class Meta:
        unique_together = (('track', 'rp_song', 'country'),)

    def __str__(self):
        return "<TrackAvailability>: {} (rp_song_id: {}) (score: {}) (id: {})".format(
            self.country, self.rp_song_id, self.score, self.id)


class TrackSearchHistory(models.Model):
    rp_song = models.OneToOneField('rphistory.Song', related_name="search_history")
    search_time = models.DateTimeField(null=False)
    found = models.BooleanField(default=False)

    def __str__(self):
        return "<TrackSearchHistory>: {} (rp_song_id: {}) (found: {}) (id: {})".format(
            self.search_time, self.rp_song_id, self.found, self.id)


class HandmappedTrack(models.Model):
    #TODO: add logic to directly map song to track for known track_id
    # The idea here would be to present a user with:
    # * the expected album title and song name from radio paradise
    # * the relevant album info from spotify (for first-matching country?)
    # * the info from e.g. amazon with album, author(s), song titles
    # The user could then say, OK, the correct artist(s)/album/song name is ..., and this data can be updated
    # in the rphistory schema, and map_tracks can be re-run to find country-specific tracks.
    rp_song = models.OneToOneField('rphistory.Song', related_name="handmapped_track")
#    spotify_album_id = models.CharField(max_length=120, help_text="Spotify album id")
    info_url = models.CharField(max_length=255, blank=True, help_text="URL to resource with information about album")
    processed = models.BooleanField(default=False)

    def __str__(self):
        return "<HandmappedTrack>: {} (rp_song_id: {}) (processed: {}) (id: {})".format(
            self.info_url, self.rp_song_id, self.processed, self.id)


def delete_references_to_rp_history_song(song_id):
    #handmapped_tracks_qs = HandmappedTrack.objects.filter(rp_song_id=song_id)
    #if log.isEnabledFor(DEBUG)
    #    for o in handmapped_tracks_qs:
    #        log.debug("Deleting object: {}".format(o))
    #handmapped_tracks_qs.delete()

    track_search_history_qs = TrackSearchHistory.objects.filter(rp_song_id=song_id)
    if log.isEnabledFor(DEBUG):
        for o in track_search_history_qs:
            log.debug("Deleting object: {}".format(o))
    track_search_history_qs.delete()

    track_qs = Track.objects.filter(trackavailability__rp_song_id=song_id).distinct()
    albums = list(Album.objects.filter(track__in=track_qs))

    # Deleting Track objects will cascade the deletions to related TrackAvailability objects.
    if log.isEnabledFor(DEBUG):
        for o in track_qs:
            log.debug("Deleting object (and related TrackAvailability objects): {}".format(o))
    track_qs.delete()

    # If any of the albums no longer have any matching tracks, delete them.
    for album in albums:
        if Track.objects.filter(album=album).count() == 0:
            if log.isEnabledFor(DEBUG):
                log.debug("Deleting album because it no longer has any associated tracks: {}".format(album))
            album.delete()

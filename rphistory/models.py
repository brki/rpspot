from django.db import models
from django.apps import apps


class Artist(models.Model):
    name = models.CharField(max_length=255, null=False, unique=True)
    songs = models.ManyToManyField('Song', related_name='artists')

    def __str__(self):
        return "<Artist: {}>".format(self.name)


class Album(models.Model):
    title = models.CharField(max_length=255, null=False, blank=True)
    asin = models.CharField(max_length=64, unique=True)
    release_year = models.IntegerField()

    def __str__(self):
        return "<Album: {} ({})>".format(self.title, self.release_year)


class UnmatchedSongQuerySet(models.QuerySet):
    def in_country(self, country):
        return self.exclude(pk__in=Song.objects.filter(available_tracks__country=country))

    def no_match_in_any_country(self):
        TrackAvailability = apps.get_model('trackmap', 'TrackAvailability')
        return self.exclude(pk__in=TrackAvailability.objects.values_list('rp_song_id', flat=True).distinct())

    def artists(self):
        return self.prefetch_related('artists').select_related('album')

    def album(self):
        return self.select_related('album')

    def search_history(self):
        return self.select_related('search_history')

    def with_order_by(self, order):
        if order == 'played':
            return self.annotate(last_played=models.Max('history__played_at')).order_by('-last_played')
        else:
            return self.order_by(order)


class Song(models.Model):
    title = models.CharField(max_length=255, null=False)
    corrected_title = models.CharField(max_length=255, null=True, blank=True)
    rp_song_id = models.IntegerField(unique=True, null=False)
    album = models.ForeignKey(Album, related_name='songs')
    isrc = models.CharField(max_length=15, null=True, blank=True)

    objects = models.Manager()
    unmatched = UnmatchedSongQuerySet.as_manager()

    def __str__(self):
        return "<Song: {}>".format(self.corrected_title or self.title)


class History(models.Model):
    song = models.ForeignKey(Song, related_name='history')
    played_at = models.DateTimeField(null=False, unique=True)

    def __str__(self):
        return "History: {} played at {}".format(self.song_id, self.played_at)

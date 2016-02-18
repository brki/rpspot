from django.db import models


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


class Song(models.Model):
    title = models.CharField(max_length=255, null=False)
    rp_song_id = models.IntegerField(unique=True, null=False)
    album = models.ForeignKey(Album, related_name='songs')

    def __str__(self):
        return "<Song: {}>".format(self.title)


class History(models.Model):
    song = models.ForeignKey(Song, related_name='history')
    played_at = models.DateTimeField(null=False, unique=True)

    def __str__(self):
        return "History: {} played at {}".format(self.song_id, self.played_at)

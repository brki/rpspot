from django.db import models

class ArtistManager(models.Manager):
    def get_or_create(self, name):
        artist = self.filter(name=name).first()
        if not artist:
            artist = self.create(name=name)
        return artist


class Artist(models.Model):
    name = models.CharField(max_length=255, null=False)

    objects = ArtistManager()

    def __unicode__(self):
        return unicode("<Artist: {}>".format(self.name))


class AlbumManager(models.Manager):
    def get_or_create(self, asin, title, release_year):
        album = self.filter(asin=asin).first()
        if not album:
            album = self.create(title=title, asin=asin, release_year=int(release_year))
        return album


class Album(models.Model):
    title = models.CharField(max_length=255, null=False)
    asin = models.CharField(max_length=64, unique=True)
    release_year = models.IntegerField()

    objects = AlbumManager()

    def __unicode__(self):
        return unicode("<Album: {} ({})>".format(self.title, self.release_year))


class SongManager(models.Manager):
    def get_or_create(self, rp_song_id, title, artist, album):
        song = self.filter(rp_song_id=rp_song_id).first()
        if not song:
            song = self.create(rp_song_id=rp_song_id, title=title, artist=artist, album=album)
        return song


class Song(models.Model):
    title = models.CharField(max_length=255, null=False)
    rp_song_id = models.IntegerField(unique=True, null=False)
    artist = models.ForeignKey(Artist, related_name='songs')
    album = models.ForeignKey(Album, related_name='songs')

    objects = SongManager()

    def __unicode__(self):
        return unicode("<Song: {}>".format(self.title))


class History(models.Model):
    song = models.ForeignKey(Song)
    played_at = models.DateTimeField(null=False, unique=True)

    def __unicode__(self):
        return unicode("History: {} played at {}".format(self.song_id, self.played_at))

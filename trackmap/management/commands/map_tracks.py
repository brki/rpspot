import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from rphistory.models import History, Song, Album, Artist
from trackmap.models import Track, TrackAvailability, TrackSearchHistory
from spotify.spotify import find_track, get_track_info

def add_song_info(song):
    info = get_market_track_info(song.title, artist=song.artist.name, album=song.album.title)

class Command(BaseCommand):
    help = 'Maps Radio Paradise playlist song to spotify tracks'

    def handle(self, *args, **options):

        new_songs = Song.objects.filter(search_history__isnull=True)
        for new_song in new_songs:
            add_song_info()


        songs = Song.objects.filter(search_history__country=search_country).filter(
            Q(search_history__isnull=True) | Q(search_history__time__lte=since)
        ).prefetch_related('search_history', 'artist', 'album')

        search_history_new = []
        search_history_updates = []
        now = timezone.now().replace(tzinfo=timezone.utc)
        for song in songs:
            result = find_track(song.title, artist=song.artist.name, album=song.album.title, country_code=country_code)
            if result:
                for market in result.available_markets:
                    track = Track.objects.get_or_create(spotify_track_uri=result.uri)
                    # Update existing TrackMap entries that have a different album_match value.
                    TrackMap.objects.filter(
                        track=track, rp_song=song, country_code__in=result.available_markets).exclude(
                        album_match=True).update(modified=now)

                    # Insert new TrackMap entries.
                    countries = Country.objects.filter(
                        code__in=result.available_markets,
                        country_trackmap__isnull=True,
                        country_trackmap__rp_song=song
                    )
                    track_maps = []
                    for country in countries:
                        track_maps.append(
                            TrackMap(track=track, rp_song=song, country=country, album_match=result.album_match)
                        )
                    TrackMap.objects.bulk_create(track_maps)

                    # Update search history




        # Find all songs that were recently added but that don't have a recent spotify mapping.
        sql = '''
          SELECT s.* FROM ({song_table} s
          LEFT OUTER JOIN {trackmap_table} t ON s.id = t.rp_song_id)
          LEFT OUTER JOIN {not_found_table} nf ON s.id = nf.rp_song_id
           WHERE t.id IS NULL
             AND nf.id IS NULL
          '''.format(song_table=Song._meta.db_table)
        recent_songs = Song.objects.raw(



        not_found = NotFoundTrack.objects.all()
        History.objects.all().prefetch_related('')

        latest_song = History.objects.all().order_by('-played_at').first()
        if latest_song:
            min_time = latest_song.played_at
        else:
            min_time = None

        latest_playlist = get_playlist_from_url()
        songs = playlist_to_python(latest_playlist, min_time=min_time)


        for song in songs:
            album = Album.objects.get_or_create(song['album_asin'], song['album'], song['album_release_year'])
            artist = Artist.objects.get_or_create(song['artist'])
            song_object = Song.objects.get_or_create(song['id'], song['title'], artist, album)
            History.objects.create(song=song_object, played_at=song['time'])

        self.stdout.write("Loaded {} new song play histories".format(len(songs)))

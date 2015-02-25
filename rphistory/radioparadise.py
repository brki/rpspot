from collections import namedtuple
from datetime import datetime
from logging import getLogger
from pytz import utc
from socket import timeout
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

from django.db import transaction
from django.db.utils import IntegrityError

from bs4 import BeautifulSoup

from rphistory.models import History, Song, Album, Artist
from .settings import RP_PLAYLIST_URL


# AsinInfo fields:
# * asin: Amazon unique id string
# * title: product title
AsinInfo = namedtuple('AsinInfo', 'asin title')

# SongInfo fields:
# time: datetime the song played on Radio Paradise (in UTC time)
# * id: Radio Paradise song id
# * title: song title
# * artist: artist name
# * album: album title
# * album_asin: Amazon unique id string
# * album_release_year: year album was released
SongInfo = namedtuple('SongInfo', 'time id title artist album album_asin album_release_year')


log = getLogger(__name__)


def playlist_to_python(xml_string, min_time=None):
    """
    :param xml_string: playlist xml string
    :param min_time: UTC datetime. If provided, only songs with a timestamp greater than this will be returned.
    """
    songs = []
    playlist = ElementTree.fromstring(xml_string)
    for song in playlist:
        time = datetime.utcfromtimestamp(float(song.find('timestamp').text)).replace(tzinfo=utc)
        if min_time and time <= min_time:
            continue

        songs.append(SongInfo(
            time=time,
            id=song.find('songid').text,
            title=song.find('title').text,
            artist=song.find('artist').text,
            album=song.find('album').text,
            album_asin=song.find('asin').text,
            album_release_year=int(song.find('release_date').text),
        ))

    sorted_songs = sorted(songs, key=lambda song: song.time)
    return sorted_songs


def save_songs_and_history(songs):
    """

    :param iterable songs: SongInfo tuples
    :return: count of songs successfully processed
    """
    loaded = 0
    for song in songs:
        try:
            with transaction.atomic():
                album_title = song.album
                if not album_title:
                    log.info(
                        "save_songs_and_history: album title missing: [title: {}, asin: {}, release_year: {}]".format(
                            song.album, song.album_asin, song.album_release_year))
                    asin_info = get_info_from_asin(song.album_asin)
                    if asin_info:
                        album_title = asin_info.title
                    else:
                        album_title = ''
                        log.info(
                            "save_songs_and_history: album title not found from asin:"
                            "[title: {}, asin: {}, release_year: {}]".format(
                                song.album, song.album_asin, song.album_release_year))
                album, _ = Album.objects.get_or_create(
                    asin=song.album_asin,
                    defaults={'title': album_title, 'release_year': song.album_release_year})
                artist, _ = Artist.objects.get_or_create(name=song.artist)
                song_object, _ = Song.objects.get_or_create(
                    rp_song_id=song.id, defaults={'title': song.title, 'artist': artist, 'album': album})
                History.objects.create(song=song_object, played_at=song.time)
                loaded += 1
        except IntegrityError as e:
            log.warn("save_songs_and_history failed to process song {}: {}".format(song, e))
            continue

    return loaded


def get_playlist_from_file(file_name):
    with open(file_name, 'r') as f:
        text = f.read()
    return text


def get_playlist_from_url(url=None):
    if url is None:
        url = RP_PLAYLIST_URL
    response = urlopen(url)
    return response.read()


def get_info_from_asin(asin):
    if not asin:
        return None
    #url = "http://www.amazon.com/exec/obidos/ASIN/{}".format(asin)
    url = "http://www.amazon.com/exec/obidos/tg/detail/-/{}".format(asin)
    try:
        page = urlopen(url, timeout=10).read()
    except (HTTPError, URLError, timeout) as err:
        log.debug("get_info_from_asin: Error opening asin url: {}".format(err))
        return None

    soup = BeautifulSoup(page)

    try:
        title = soup.find(id='productTitle').string
    except AttributeError as err:
        log.debug("get_info_from_asin: Unable to get product title: {}".format(err))
        return None

    return AsinInfo(asin=asin, title=title)

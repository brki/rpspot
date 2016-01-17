from collections import namedtuple
from datetime import datetime
from logging import getLogger
from pytz import utc
from socket import timeout
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

from django.core.cache import caches
from django.db import transaction
from django.db.utils import IntegrityError

from bs4 import BeautifulSoup

from rphistory.models import History, Song, Album, Artist
from .settings import RP_PLAYLIST_URL, RP_CACHE


# AsinInfo fields:
# * asin: Amazon unique id string
# * title: product title
# * authors: array of author names
# * tracks: array of tracks
AsinInfo = namedtuple('AsinInfo', 'asin title authors tracks')

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


def rphistory_cache():
    return caches[RP_CACHE]


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

    sorted_songs = sorted(songs, key=lambda s: s.time)
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
                    rp_song_id=song.id, defaults={'title': song.title, 'album': album})
                song_object.artists.add(artist)
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
    etag_cache_key = 'rphistory:etag:' + url
    cache = rphistory_cache()
    old_etag = cache.get(etag_cache_key)

    response = get_response_if_modified(url, old_etag)
    if response is None:
        return None

    try:
        current_etag = response.headers['Etag']
        cache.set(etag_cache_key, current_etag, None)
    except AttributeError:
        # For some reason there is no Etag header.  Clear the cache for the Etag.
        log.warn("Playlist is not providing an Etag header")
        if old_etag:
            cache.set(etag_cache_key, '', 0)
    return response.read()


def get_response_if_modified(url, etag=None):
    if etag:
        headers = {'If-None-Match': etag}
    else:
        headers = {}
    req = Request(url, headers=headers)
    try:
        response = urlopen(req)
        return response
    except HTTPError as e:
        if e.code == 304:
            return None
        else:
            raise


def get_info_from_asin(asin):
    if not asin:
        return None
    # alternative: url = "http://www.amazon.com/exec/obidos/ASIN/{}".format(asin)
    url = "http://www.amazon.com/exec/obidos/tg/detail/-/{}".format(asin)
    try:
        page = urlopen(url, timeout=10).read()
    except (HTTPError, URLError, timeout) as err:
        log.warn("get_info_from_asin: Error opening asin url: {}".format(err))
        return None

    soup = BeautifulSoup(page)

    try:
        title = soup.find(id='productTitle').string
    except AttributeError as err:
        log.warn("get_info_from_asin: Unable to get product title: {}".format(err))
        return None

    authors = []
    author_spans = soup.select('span.author')
    for author in author_spans:
        try:
            authors.append(author.a.string)
        except AttributeError:
            authors.append(author.string)

    # Try to get tracks from non-mp3 sample tracks listing
    tracks = [t.string.strip() for t in soup.select('#musicTracksFeature div.content td')]
    if not tracks:
        # Try to get tracks from mp3 sample tracks listing
        tracks = [t.text.strip() for t in soup.select('div#albumTrackList td.titleCol')]
    if not tracks:
        # Try to get tracks from singles-style listing
        tracks = []


    if not tracks:
        tracks = None

    return AsinInfo(asin=asin, title=title, authors=authors, tracks=tracks)

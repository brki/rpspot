from datetime import datetime
from operator import itemgetter
from pytz import utc
from urllib.request import urlopen
from xml.etree import ElementTree
from .settings import RP_PLAYLIST_URL


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

        songs.append({
            'time': time,
            'id': song.find('songid').text,
            'title': song.find('title').text,
            'artist': song.find('artist').text,
            'album': song.find('album').text,
            'album_asin': song.find('asin').text,
            'album_release_year': song.find('release_date').text,
        })

    sorted_songs = sorted(songs, key=itemgetter('time'))
    return sorted_songs

def get_playlist_from_file(file_name):
    with open(file_name, 'r') as f:
        text = f.read()
    return text

def get_playlist_from_url(url=None):
    if url is None:
        url = RP_PLAYLIST_URL
    response = urlopen(url)
    return response.read()

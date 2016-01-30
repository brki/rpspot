from django.db import connection

def history(time_start, time_end, country):
    """
    Gets the Radio Paradise song history as a json array, with the associated Spotify
    track for each song, if any.

    :param datetime time_start:
    :param datetime time_end:
    :param string country: two letter country code
    :return: json string with array of results
    """

    # TODO cache with a key "country + time_start (minute precision) + time_end (minute precision)"

    sql = """
    SELECT h.played_at, s.title, artist.name as artist_name, album.title as album_title, track.spotify_id AS spotify_track_id,
           spot_album.img_small_url AS spotify_album_img_small_url, spot_album.img_large_url AS spotify_album_img_large_url
     FROM rphistory_history h
     JOIN rphistory_song s ON h.song_id = s.id
     JOIN rphistory_artist_songs ras ON s.id = ras.song_id
     JOIN rphistory_artist artist ON artist.id = ras.artist_id
     JOIN rphistory_album album ON album.id = s.album_id
     LEFT OUTER JOIN trackmap_trackavailability ta ON ta.rp_song_id = s.id AND ta.country = %s
     LEFT OUTER JOIN trackmap_track track ON track.id = ta.track_id
     LEFT OUTER JOIN trackmap_album spot_album ON spot_album.id = track.album_id
     WHERE h.played_at BETWEEN %s AND %s
     ORDER BY h.played_at DESC
    """
    params = [country, time_start, time_end]

    pretty_print_json = 'true'
    json_sql = "SELECT array_to_json(array_agg(row_to_json(t, {})), {})" \
        " FROM (".format(pretty_print_json, pretty_print_json) + sql + ") t"

    cursor = connection.cursor()
    cursor.execute(json_sql, params)
    result = cursor.fetchone()[0]
    return result or '[]'


def last_24_hours(country):
    pass
    # TODO call history, cache the result.
    # Update caller of history() to use this method when appropriate.
    # Invalidate cache when new song arrives.

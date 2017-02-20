from django.db import connection


def history(country,
            l2_where_clause="1", l2_order_by_clause='', l2_limit_clause='', l2_params=None,
            l1_limit_clause='', l1_params=None):

    l2_params = l2_params or []
    l1_params = l1_params or []
    # Reference country is the one that is used to find tracks, as long as the Spotify API is no longer providing
    # all the country details when searching, or until another workaround is made.
    reference_country = 'CH'
    params = [country, country, reference_country] + l2_params + l1_params

    # Subquery with DISTINCT is used to eliminate some duplicate artist -> track mappings that happen
    # where Radio Paradise changes song artist information and that song is reprocessed by the map_tracks command.
    # There are also some duplicate entries for songs that were reported played at, for example, 12:30:00 AND
    # 12:30:00.120999.
    sql = """
    SELECT DISTINCT ON (played_at)
      date_trunc('second', played_at_time) AS played_at,
      rp_song_id,
      title,
      artist_name,
      album_title,
      asin,
      spotify_track_id,
      spotify_album_img_small_url,
      spotify_album_img_large_url,
      coalesce(country_match, FALSE) AS country_match
     FROM (
        SELECT * FROM (
            SELECT h.played_at AS played_at_time,
                   s.rp_song_id,
                   COALESCE(s.corrected_title, s.title) AS title,
                   artist.name AS artist_name,
                   album.title AS album_title,
                   album.asin,
                   track.spotify_id AS spotify_track_id,
                   spot_album.img_medium_url AS spotify_album_img_small_url,
                   spot_album.img_large_url AS spotify_album_img_large_url,
                   artist.id AS artist_id,
                   ta.country = %s AS country_match
             FROM rphistory_history h
             JOIN rphistory_song s ON h.song_id = s.id
             JOIN rphistory_artist_songs ras ON s.id = ras.song_id
             JOIN rphistory_artist artist ON artist.id = ras.artist_id
             JOIN rphistory_album album ON album.id = s.album_id
             LEFT OUTER JOIN trackmap_trackavailability ta ON ta.rp_song_id = s.id AND (ta.country = %s OR ta.country = %s)
             LEFT OUTER JOIN trackmap_track track ON track.id = ta.track_id
             LEFT OUTER JOIN trackmap_album spot_album ON spot_album.id = track.album_id
             WHERE {l2_where_clause}
             {l2_order_by_clause}
             {l2_limit_clause}
         ) subq_l2
         {l1_limit_clause}
     ) subq_l1
    ORDER BY played_at DESC, country_match DESC, artist_id DESC
    """.format(
        l2_where_clause=l2_where_clause,
        l2_order_by_clause=l2_order_by_clause,
        l2_limit_clause=l2_limit_clause,
        l1_limit_clause=l1_limit_clause
    )
    pretty_print_json = 'true'
    json_sql = "SELECT array_to_json(array_agg(row_to_json(t, {})), {})" \
        " FROM (".format(pretty_print_json, pretty_print_json) + sql + ") t"

    cursor = connection.cursor()
    cursor.execute(json_sql, params)
    result = cursor.fetchone()[0]
    return result or '[]'


def json_history_count_vector(country, base_time, count_vector):
    """
    Gets the Radio Paradise song history as a json array, with the associated Spotify
    track for each song, if any.

    A positive value for ``count_vector`` will fetch results with a played_at datetime >= base_time,
    a negative value will fetch results with a played_at datetime <= base_time.

    :param string country: two letter country code
    :param datetime base_time:
    :param int count_vector: positive/negative int: how many results to return and in which direction from start_time
    :return: json string with array of results
    """
    if count_vector < 0:
        comparator = '<='
        l2_order_by_direction = 'DESC'
    else:
        comparator = '>='
        l2_order_by_direction = 'ASC'

    count = min(400, abs(count_vector))

    l2_where_clause = "h.played_at {} %s".format(comparator)
    l2_order_clause = "ORDER BY played_at {}".format(l2_order_by_direction)
    # The l2_limit is larger than count, to allow for possible duplicate values and songs that are not available
    # in the region.
    l2_limit_clause = "LIMIT {}".format(count * 2)
    l1_limit_clause = "LIMIT {}".format(count)

    return history(
        country=country,
        l2_where_clause=l2_where_clause,
        l2_order_by_clause=l2_order_clause,
        l2_limit_clause=l2_limit_clause,
        l2_params=[base_time],
        l1_limit_clause=l1_limit_clause
    )


def json_history_date_period(country, time_start, time_end):
    """
    Gets the Radio Paradise song history as a json array, with the associated Spotify
    track for each song, if any.

    :param string country: two letter country code
    :param datetime time_start:
    :param datetime time_end:
    :return: json string with array of results
    """
    # TODO cache with a key "country + time_start (minute precision) + time_end (minute precision)"
    return history(
        country=country,
        l2_where_clause="h.played_at BETWEEN %s AND %s",
        l2_params=[time_start, time_end]
    )


def last_24_hours(country):
    pass
    # TODO call history, cache the result.
    # Update caller of history() to use this method when appropriate.
    # Invalidate cache when new song arrives.

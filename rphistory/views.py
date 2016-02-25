from urllib.parse import urlencode
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from trackmap import trackmap
from .models import Song


@login_required
def unmatched(request, country=None, page=1):
    order = request.GET.get('order', None)
    if order == 'artist':
        order = 'artists__name'
    elif order == 'id':
        order = 'id'
    else:
        order = 'played'

    page = max(int(page), 1)
    page_size = 100
    start = page_size * (page - 1)
    end = page_size * page

    if country:
        qs = Song.unmatched.in_country(country)
    else:
        qs = Song.unmatched.no_match_in_any_country()
    qs = qs.artists().album().with_order_by(order)[start:end]

    track_search = trackmap.TrackSearch()

    songs = []
    for s in qs:
        song = []
        artists = s.artists.all()
        artist_list = ', '.join(['{} [{}]'.format(a.name, a.id) for a in artists])
        search_string = 'spotify {} {}'.format(
            s.corrected_title or s.title,
            " ".join([a.name for a in artists])
        )
        query_string = urlencode({'q': search_string})
        rp_url = 'https://www.radioparadise.com/rp_2.php?#name=songinfo&song_id={}'.format(s.rp_song_id)
        query_info = track_search.spotify_query(s)
        spotify_query = " / ".join([query for query, _, _, _ in query_info])

        song.append({'label': 'Artists', 'value': artist_list, 'type': 'text'})
        song.append({'label': 'Title', 'value': s.title, 'type': 'text'})
        if s.corrected_title:
            song.append({'label': 'Corrected title', 'value': s.corrected_title, 'type': 'text'})
        song.append({'label': 'Album', 'value': s.album.title, 'type': 'text'})
        if hasattr(s, 'last_played'):
            song.append({'label': 'Last played', 'value': s.last_played, 'type': 'text'})
        song.append({'label': 'RP URL', 'value': rp_url, 'type': 'url'})
        song.append({'label': 'rp_song_id', 'value': s.rp_song_id, 'type': 'text'})
        song.append({'label': 'Spotify query', 'value': spotify_query, 'type': 'text'})
        song.append({'label': 'ASIN', 'value': 'http://www.amazon.com/exec/obidos/ASIN/{}'.format(s.album.asin), 'type': 'url'})
        song.append({'label': 'Google it', 'value': 'https://google.com/search?{}'.format(query_string), 'type': 'url'})

        songs.append(song)

    return render(request, 'rphistory/unmatched_songs.html', {'songs': songs})

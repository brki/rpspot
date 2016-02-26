import datetime
from urllib.parse import urlencode

from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from trackmap import trackmap
from .models import Song
from trackmap.models import TrackSearchHistory


def redirect_or_text_response(request, text="Thanks"):
    redirect_to = request.POST.get('redirect_to', None)
    if redirect_to:
        if not redirect_to.startswith('/history/unmatched/'):
            raise ValueError('invalid redirect_to value')
        return redirect(redirect_to)

    return HttpResponse(text)


@login_required
def unmatched(request, country=None, page=1):
    order = request.GET.get('order', None)
    if order == 'artist':
        order = 'artists__name'
    elif order == 'id':
        order = 'id'
    else:
        order = 'played'

    min_time_since_last_manual_check = request.GET.get('last_manual', None)
    if min_time_since_last_manual_check is not None:
        min_time_since_last_manual_check = int(min_time_since_last_manual_check)


    page = max(int(page), 1)
    page_size = 100
    start = page_size * (page - 1)
    end = page_size * page

    if country:
        qs = Song.unmatched.in_country(country)
    else:
        qs = Song.unmatched.no_match_in_any_country()

    if min_time_since_last_manual_check is not None:
        since = datetime.datetime.now() - datetime.timedelta(days=min_time_since_last_manual_check)
        qs = qs.filter(
            Q(search_history__last_manual_check__isnull=True) |
            Q(search_history__last_manual_check__lte=since)
        )

    qs = qs.artists().album().search_history().with_order_by(order)[start:end]

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
        song.append({'label': 'song id', 'value': s.id, 'type': 'text'})
        song.append({'label': 'last manual check', 'value': s.search_history.last_manual_check, 'type': 'text'})
        song.append({'label': 'Spotify query', 'value': spotify_query, 'type': 'text'})
        song.append({'label': 'ASIN', 'value': 'http://www.amazon.com/exec/obidos/ASIN/{}'.format(s.album.asin), 'type': 'url'})
        song.append({'label': 'Google it', 'value': 'https://google.com/search?{}'.format(query_string), 'type': 'url'})

        action_info = {
            'checked_action_url': reverse('manually_checked', args=[s.id]),
            'checked_button_text': 'Mark checked',
            'retry_action_url': reverse('retry', args=[s.id]),
            'retry_button_text': 'Retry search',
            'redirect_url': request.get_full_path(),
        }
        song.append({'label': 'Actions', 'value': action_info, 'type': 'actions_info'})

        songs.append(song)

    return render(request, 'rphistory/unmatched_songs.html', {'songs': songs})


@login_required
@require_POST
def manually_checked(request, song_id):
    search_history = get_object_or_404(TrackSearchHistory, rp_song_id=song_id)
    search_history.last_manual_check = datetime.datetime.now()
    search_history.save()

    return redirect_or_text_response(request)


@login_required
@require_POST
def retry(request, song_id):
    song = get_object_or_404(Song, pk=song_id)

    call_command('map_tracks', force=True, rp_song_id=song.rp_song_id)

    return redirect_or_text_response(request)

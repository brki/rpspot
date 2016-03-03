import datetime
import re
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


isrc_pattern = re.compile(r'^[a-z]{2}[a-z0-9]{3}[0-9]{2}\d{5}$', re.IGNORECASE)


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

    unmatched_count = qs.count()
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
        spotify_query = " / ".join([query for query, _, _, _, _ in query_info])

        song.append({'label': 'Title', 'value': s.title, 'type': 'text', 'id': 'song_title'})
        if s.corrected_title:
            song.append({'label': 'Corrected title', 'value': s.corrected_title, 'type': 'text', 'id': 'corrected_title_static'})
        song.append({'label': 'Artists', 'value': artist_list, 'type': 'text', 'id': 'artists_name'})
        song.append({'label': 'Album', 'value': s.album.title, 'type': 'text', 'id': 'album_title'})
        if hasattr(s, 'last_played'):
            song.append({'label': 'Last played', 'value': s.last_played, 'type': 'text', 'id': 'last_played'})
        song.append({'label': 'RP URL', 'value': rp_url, 'type': 'url', 'id': 'rp_url'})
        song.append({'label': 'rp_song_id', 'value': s.rp_song_id, 'type': 'text', 'id': 'rp_song_id'})
        song.append({'label': 'song id', 'value': s.id, 'type': 'text', 'id': 'song_id'})
        song.append({'label': 'last manual check', 'value': s.search_history.last_manual_check, 'type': 'text', 'id': 'last_manual_check'})
        song.append({'label': 'Spotify query', 'value': spotify_query, 'type': 'text', 'id': 'spotify_query'})
        song.append({'label': 'ASIN', 'value': 'http://www.amazon.com/exec/obidos/ASIN/{}'.format(s.album.asin), 'type': 'url', 'id': 'asin'})
        song.append({'label': 'Google it', 'value': 'https://google.com/search?{}'.format(query_string), 'type': 'url', 'id': 'google_it'})

        action_info = {
            'checked_action_url': reverse('manually_checked', args=[s.id]),
            'checked_button_text': 'Mark checked',
            'retry_action_url': reverse('retry', args=[s.id]),
            'retry_button_text': 'Retry search',
            'correct_title_action_url': reverse('correct_title', args=[s.id]),
            'correct_title_button_text': 'Correct title / retry search',
            'song_title': s.corrected_title or s.title,
            'redirect_url': request.get_full_path(),
            'isrc': s.isrc or '',
            'isrc_action_url': reverse('set_isrc', args=[s.id]),
            'isrc_button_text': 'Set ISRC'
        }
        song.append({'label': 'Actions', 'value': action_info, 'type': 'actions_info', 'id': 'action_list'})

        songs.append(song)

    return render(request, 'rphistory/unmatched_songs.html', {'songs': songs, 'unmatched_count': unmatched_count})


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


@login_required
@require_POST
def correct_title(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    correct_title = request.POST.get('correct_title', None)

    if correct_title in [song.title, song.corrected_title]:
        return HttpResponse("Song already has this title")

    song.corrected_title = correct_title.strip()
    song.save()

    call_command('map_tracks', force=True, rp_song_id=song.rp_song_id)

    return redirect_or_text_response(request)


@login_required
@require_POST
def set_isrc(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    isrc = request.POST.get('isrc', '').strip()

    if not isrc_pattern.match(isrc):
        return HttpResponse("This doesn't look like a valid ISRC", status=400)

    song.isrc = isrc
    song.save()

    call_command('map_tracks', force=True, rp_song_id=song.rp_song_id)

    return redirect_or_text_response(request)

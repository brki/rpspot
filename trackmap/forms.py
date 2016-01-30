from django import forms
from django.utils.translation import ugettext as _
from trackmap.models import TrackAvailability
from trackmap.settings import (
    TIMEZONE_SELECT, COUNTRY_CODES, TRACKMAP_DEFAULT_TRACK_LIMIT, TRACKMAP_DEFAULT_COUNTRY, TRACKMAP_DEFAULT_TIMEZONE)


def country_choices():
    markets = TrackAvailability.objects.all_markets(force_cache_refresh=False)
    choices = tuple([(market, COUNTRY_CODES[market]) for market in markets])
    return sorted(choices, key=lambda c: c[1])


class PlaylistOptions(forms.Form):
    limit = forms.IntegerField(
        label=_("Track count"), min_value=1, max_value=100, required=False, initial=TRACKMAP_DEFAULT_TRACK_LIMIT)
    country = forms.ChoiceField(
        choices=country_choices(), label="Spotify account country", initial=TRACKMAP_DEFAULT_COUNTRY)
    start_time = forms.DateTimeField(label=_("Start playlist at"), required=False)
    timezone = forms.ChoiceField(
        choices=TIMEZONE_SELECT, label=_("Time zone"), initial=TRACKMAP_DEFAULT_TIMEZONE)

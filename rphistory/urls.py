from django.conf.urls import include, url

from .views import correct_title, manually_checked, retry, set_isrc, unmatched


urlpatterns = [
    url(r'^unmatched/$', unmatched, name='unmatched_anywhere'),
    url(r'^unmatched/(?P<page>[0-9]{1,5})/$', unmatched, name='unmatched_anywhere_page'),
    url(r'^unmatched/(?P<country>[A-Z]{2})/$', unmatched, name='unmatched_html'),
    url(r'^unmatched/(?P<country>[A-Z]{2})/(?P<page>[0-9]{1,5})/$', unmatched, name='unmatched_page_html'),

    url(r'^unmatched/checked/(?P<song_id>\d+)/$', manually_checked, name='manually_checked'),
    url(r'^unmatched/retry/(?P<song_id>\d+)/$', retry, name='retry'),
    url(r'^unmatched/correct_title/(?P<song_id>\d+)/$', correct_title, name='correct_title'),
    url(r'^unmatched/isrc/(?P<song_id>\d+)/$', set_isrc, name='set_isrc'),
]

from django.conf.urls import url
from rest import views
from .views import UnmatchedSongList


urlpatterns = [
    url(r'^history/(?P<country>[A-Z]{2})/$', views.history, name='history'),
    url(r'^unmatched/(?P<country>[A-Z]{2})/$', UnmatchedSongList.as_view(), name='unmatched'),
]
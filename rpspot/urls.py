from django.conf.urls import include, url
from django.contrib import admin
from trackmap.views import playlist
import rest.urls


urlpatterns = [
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^rest/', include(rest.urls)),
    url(r'^spotify-playlist/radio-paradise/$', playlist, name='playlist'),
]

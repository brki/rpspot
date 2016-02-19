from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from trackmap.views import playlist
import rest.urls


urlpatterns = [
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^rest/', include(rest.urls)),
    url(r'^spotify-playlist/radio-paradise/$', playlist, name='playlist'),
    url(r'^history/', include('rphistory.urls')),

    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, name='logout'),
]

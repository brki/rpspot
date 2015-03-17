from django.conf.urls import include, url
from django.contrib import admin
from trackmap.views import playlist


urlpatterns = [
    # Examples:
    # url(r'^$', 'rpspot.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^spotify-playlist/radio-paradise/$', playlist, name='playlist')
]
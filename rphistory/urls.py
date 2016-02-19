from django.conf.urls import include, url
from .views import unmatched


urlpatterns = [
    url(r'^unmatched/(?P<country>[A-Z]{2})/$', unmatched, name='unmatched_html'),
    url(r'^unmatched/(?P<country>[A-Z]{2})/(?P<page>[0-9]{1,5})/$', unmatched, name='unmatched_page_html'),
]

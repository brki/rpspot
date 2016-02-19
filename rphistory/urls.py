from django.conf.urls import include, url
from .views import current_datetime


urlpatterns = [
    url(r'^test/$', current_datetime, name='test'),
]

from django.conf.urls import url
from rest import views


urlpatterns = [
    url(r'^history/(?P<country>[A-Z]{2})/$', views.history, name='history')
]
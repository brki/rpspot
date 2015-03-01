from django.conf import settings

RP_PLAYLIST_BASE = getattr(settings, 'RP_PLAYLIST_BASE', 'https://www.radioparadise.com/xml/')
RP_PLAYLIST_URL = getattr(settings, 'RP_PLAYLIST_URL', 'https://www.radioparadise.com/xml/playlist.xml')
RP_CACHE = getattr(settings, 'RP_CACHE', 'default')

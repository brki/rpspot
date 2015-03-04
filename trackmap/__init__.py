from django.conf import settings
from django.utils.cache import caches

def trackmap_cache():
    return caches[settings.TRACKMAP_CACHE]
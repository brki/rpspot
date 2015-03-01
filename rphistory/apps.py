from django.apps import AppConfig


class RpHistoryConfig(AppConfig):
    name = 'rphistory'
    verbose_name = "Radio Paradise History"
    cache_cleared = False

    def ready(self):
        if not self.cache_cleared:
            from rphistory.radioparadise import rphistory_cache
            rphistory_cache().clear()
            self.cache_cleared = True

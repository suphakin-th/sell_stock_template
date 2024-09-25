
from django.core.exceptions import EmptyResultSet
from django.db import models
import hashlib
from django.core.cache import cache
from utils.caches.time_out import get_time_out_minute


class CacheWithHashKeyUtils:
    @staticmethod
    def cache_with_hash_key(key: str, fn_get_value, timeout=None):
        if timeout is None:
            timeout = get_time_out_minute()
        key = hashlib.md5(key.encode()).hexdigest()[:8]
        result = cache.get(key)
        if result is None:
            result = fn_get_value()
            cache.set(key, result, timeout)
        return result


class CacheHashCountQuerySet(models.QuerySet):
    def count(self):
        try:
            key = str(self.query)
            result = CacheWithHashKeyUtils.cache_with_hash_key(key, super().count)
        except EmptyResultSet as e:
            result = super().count()
        return result


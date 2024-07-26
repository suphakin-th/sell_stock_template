from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache

from account.models import Account
from utils.caches.time_out import get_time_out
from utils.redis import delete_value


def cache_account(account_id):
    key = 'account_%s' % account_id
    result = cache.get(key)
    if result is None:
        try:
            result = Account.objects.get(id=account_id)
        except:
            result = -1
        cache.set(key, result, get_time_out())
    return None if result == -1 else result


def cache_account_delete(account_id):
    key = 'account_%s' % account_id
    cache.delete(key)
    cache.delete('account_profile_%s' % account_id)
    cache.delete('auth_group_list_%s' % account_id)
    cache.delete('auth_permission_%s' % account_id)

    # Delete Redis Cached
    delete_value(key)


def cache_user_account_id_list():
    key = 'user_account_id_list'
    result = cache.get(key)
    if result is None:
        result = list(Account.objects.exclude(type=1).values_list('id', flat=True))
        cache.set(key, result, get_time_out())
    return None if result == -1 else result

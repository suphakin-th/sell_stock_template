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
    
def cached_account_profile(account_id):
    from account.serializers import AccountSerializer
    key = 'account_profile_%s' % account_id
    result = cache.get(key)
    if result is None:
        try:
            account = Account.objects.get(id=account_id)
            result = AccountSerializer(account).data
            cache.set(key, result, get_time_out())
            return result
        except:
            result = {}
    if result:
        # TODO: seperate api profile dataconsent
        account = Account.objects.get(id=account_id)
        result['is_accepted_term'] = account.is_accepted_term
        result['is_accepted_privacy'] = account.is_accepted_privacy
        result['is_accepted_data_consent'] = account.is_accepted_data_consent
    return result


def cache_user_account_id_list():
    key = 'user_account_id_list'
    result = cache.get(key)
    if result is None:
        result = list(Account.objects.exclude(type=1).values_list('id', flat=True))
        cache.set(key, result, get_time_out())
    return None if result == -1 else result

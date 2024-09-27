from django.core.cache import cache

from utils.caches.time_out import get_time_out
from .models import Count, Inbox


def cache_account_count(account):
    key = 'inbox_count_account_%s' % account.id
    result = cache.get(key)
    if result is None:
        result = Count.objects.filter(account_id=account.id, is_dashboard=False).first()
        if result is None:
            result = Count.objects.create(account=account, is_dashboard=False)
        cache.set(key, result, get_time_out())
    return result


def cache_account_count_delete(account_id):
    key = 'inbox_count_account_%s' % account_id
    cache.delete(key)


def cache_account_count_unread(account):
    key = 'inbox_count_account_unread_%s' % account.id
    result = cache.get(key)
    if result is None:
        result = Inbox.objects.filter(status=1,
                                      member__account=account,
                                      read__isnull=True,
                                      is_dashboard=False).count()
        cache.set(key, result, get_time_out())
    return result


def cache_account_count_unread_delete(account):
    key = 'inbox_count_account_unread_%s' % account.id
    cache.delete(key)


def cache_dashboard_account_count(account):
    key = 'inbox_dashboard_count_account_%s' % account.id
    result = cache.get(key)
    if result is None:
        result = Count.objects.filter(account_id=account.id, is_dashboard=True).first()
        if result is None:
            result = Count.objects.create(account=account, is_dashboard=True)
        cache.set(key, result, get_time_out())
    return result


def cache_dashboard_account_count_delete(account):
    key = 'inbox_dashboard_count_account_%s' % account.id
    cache.delete(key)


def cache_dashboard_account_count_unread(account):
    key = 'inbox_dashboard_count_account_unread_%s' % account.id
    result = cache.get(key)
    if result is None:
        result = Inbox.objects.filter(status=1,
                                      member__account=account,
                                      read__isnull=True,
                                      is_dashboard=True).count()
        cache.set(key, result, get_time_out())
    return result


def cache_dashboard_account_count_unread_delete(account):
    key = 'inbox_dashboard_count_account_unread_%s' % account.id
    cache.delete(key)

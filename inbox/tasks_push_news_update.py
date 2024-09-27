from django.conf import settings
from celery import shared_task

from account.models import Account
from news_update.models import NewsUpdate
from utils.celery.lock import task_lock
from .models import Inbox
from rest_framework import status
from notification_template.models import Trigger
from config.models import Config


@shared_task(bind=True, queue='user')
def task_push_news_update(self, news_update_id):
    news_update = NewsUpdate.objects.filter(id=news_update_id).first()
    if news_update is None:
        return None

    if not NewsUpdate.objects.filter(id=news_update_id, is_notification=True).first():
        return None

    if Inbox.objects.filter(content_type=settings.CONTENT_TYPE('news_update.newsupdate'),
                            content_id=news_update.id).exists():
        return None

    account_list = Account.objects.filter(is_active=True).exclude(email__isnull=True)
    title = 'You received News Updates'
    # inbox = Inbox.push(
    #     sender=news_update.account,
    #     inbox_type=2,
    #     inbox_content_id=news_update.id,
    #     inbox_content_type=settings.CONTENT_TYPE('news_update.newsupdate'),
    #     title=title,
    #     body=news_update.name,
    #     account_list=account_list
    # )
    # inbox.send_notification()
    trigger = Trigger.get_code('n_u_noti')
    trigger.send_notification(
        sender=None,
        inbox_type=2,
        inbox_content_id=news_update.id,
        inbox_content_type=settings.CONTENT_TYPE('news_update.newsupdate'),
        title=title,
        body='',
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_news_update_force_send(self, news_update_id):
    lock_id = f'{self.name}.{self.request.id}.lock'
    lock_expire = 10 * 60 * 60  # expire 10 hours

    with task_lock(lock_id, self.app.oid, lock_expire) as acquired:
        if not acquired:
            return f'{self.request.id} is already being executed by another work'

    news_update = NewsUpdate.objects.filter(id=news_update_id).first()
    if news_update is None:
        return None

    if not NewsUpdate.objects.filter(id=news_update_id, is_notification=True).first():
        return None

    header_image = Config.pull_value('mailer-header-image')
    account_list = Account.objects.filter(is_active=True).exclude(email__isnull=True)
    title = 'You received News Updates'
    # trigger = Trigger.get_code('cancel')
    # payload = {
    #     'content_name': content.name,
    #     'site': site
    # }
    # template = trigger.current_template
    # title = template.get_subject(**payload)
    # body = template.get_body(**payload)

    # inbox = Inbox.push(
    #     sender=news_update.account,
    #     inbox_type=2,
    #     inbox_content_id=news_update.id,
    #     inbox_content_type=settings.CONTENT_TYPE('news_update.newsupdate'),
    #     title=title,
    #     body=news_update.name,
    #     # body='',
    #     account_list=account_list
    # )
    # inbox.send_notification('n_u_noti')
    trigger = Trigger.get_code('n_u_noti')
    trigger.send_notification(
        sender=None,
        inbox_type=2,
        inbox_content_id=news_update.id,
        inbox_content_type=settings.CONTENT_TYPE('news_update.newsupdate'),
        title=title,
        body='',
        account_list=account_list
    )

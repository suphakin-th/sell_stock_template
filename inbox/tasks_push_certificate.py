from celery import shared_task
from django.conf import settings

from inbox.models import Inbox
from inbox.utils import get_dashboard_receive_account_id_list
from notification_template.models import Trigger
from utils.content_v2 import get_content


@shared_task(bind=True, queue='user')
def task_push_approve_certificate(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    inbox_type = 40
    title = 'Congratulations! You received an E-Certificate'
    body = ''

    account_list = [progress.account]
    # inbox_qs = Inbox.objects.filter(
    #     type=inbox_type,
    #     content_type=progress_content_type,
    #     content_id=progress.id,
    # )
    # if inbox_qs.exists():
    #     return 'No sent'
    trigger = Trigger.get_code('app_cert')

    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=progress_content_type,
        inbox_content_id=progress.id,
        content_id=progress.content_id,
        content_type=_content_type,
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_unapproved_certificate(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    inbox_type = 41
    title = 'Sorry, your E-Certificate has been unapproved'
    body = ''
    # inbox_qs = Inbox.objects.filter(
    #     type=inbox_type,
    #     content_type=progress_content_type,
    #     content_id=progress.id,
    # )
    # if inbox_qs.exists():
    #     return 'No sent'
    account_list = [progress.account]
    trigger = Trigger.get_code('unapp_cert')
    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=progress_content_type,
        inbox_content_id=progress.id,
        content_id=progress.content_id,
        content_type=_content_type,
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='dashboard')
def task_push_notify_approve_certificate(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    inbox_type = 42
    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=progress_content_type,
        content_id=progress.id,
    )
    if inbox_qs.exists():
        return 'No sent'
    account_id_list = get_dashboard_receive_account_id_list(_content_type.id, content.id)
    trigger = Trigger.get_code('notify_approve_certificate')
    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=progress_content_type,
        inbox_content_id=progress.id,
        content_id=progress.content_id,
        content_type=_content_type,
        account_list=account_id_list,
        is_dashboard=trigger.is_dashboard
    )


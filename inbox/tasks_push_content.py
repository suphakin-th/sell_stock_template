from django.conf import settings
from celery import shared_task

from event.models import Event
from transaction.models import Transaction
from utils.content import get_content
from .models import Inbox
from notification_template.models import Trigger
from .utils import get_dashboard_receive_account_id_list


@shared_task(bind=True, queue='user')
def task_push_content_start(self, inbox_type, title, content_type_id, content_id):
    body = ''
    detail = ''
    account_id_list = Transaction.objects.filter(
        content_type_id=content_type_id,
        content_id=content_id,
        status=0
    ).values_list('account_id', flat=True)

    # if inbox_type == 30:
    #     trigger = Trigger.get_code('con_start')
    #     trigger.send_notification(
    #         sender=None,
    #         inbox_type=inbox_type,
    #         content_id=content_id,
    #         content_type=settings.CONTENT_TYPE_ID(content_type_id),
    #         title=title,
    #         body=body,
    #         account=account_id_list
    #     )
    # elif inbox_type == 31:
    #     trigger = Trigger.get_code('con_before')
    #     trigger.send_notification(
    #         sender=None,
    #         inbox_type=inbox_type,
    #         content_id=content_id,
    #         content_type=settings.CONTENT_TYPE_ID(content_type_id),
    #         title=title,
    #         body=body,
    #         account=account_id_list
    #     )

    inbox = Inbox.push(
        sender=None,
        inbox_content_type=settings.CONTENT_TYPE_ID(content_type_id),
        inbox_content_id=content_id,
        inbox_type=inbox_type,
        title=title,
        body=body,
        detail=detail,
        account_list=account_id_list
    )
    inbox.send_notification()


@shared_task(bind=True, queue='user')
def task_push_content_cancelled(self, content_type_id, content_id):
    content = get_content(content_type_id, content_id)
    if content:
        if isinstance(content, Event):
            event_program_name = content.event_program.name if content.event_program else ''
            title = 'Sorry, this %s (%s) has been canceled!' % (event_program_name, content.name)
        else:
            title = 'Sorry, this %s has been canceled!' % content.name
    else:
        title = 'Sorry, this %s has been canceled!' % settings.CONTENT_TYPE_ID(content_type_id).app_label
    body = ''
    inbox_type = 32
    account_list = Transaction \
        .pull_list_by_content(content_id=content_id, content_type=settings.CONTENT_TYPE_ID(content_type_id)) \
        .filter(status=-4) \
        .values_list('account_id', flat=True)

    # inbox = Inbox.push(
    #     sender=None,
    #     inbox_type=inbox_type,
    #     inbox_content_id=content_id,
    #     inbox_content_type=settings.CONTENT_TYPE_ID(content_type_id),
    #     title=title,
    #     body=body,
    #     account_list=account_list
    # )
    # inbox.send_notification('cancelled')
    trigger = Trigger.get_code('cancelled')
    trigger.send_notification(
            sender=None,
            inbox_type=inbox_type,
            inbox_content_id=content_id,
            inbox_content_type=settings.CONTENT_TYPE_ID(content_type_id),
            title=title,
            body=body,
            account_list=account_list
    )


@shared_task(bind=True, queue='dashboard')
def task_push_new_content_permission(self, content_type_id, content_id, account_id):
    inbox_type = 34
    account_id_list = get_dashboard_receive_account_id_list(content_type_id, content_id, account_id)
    trigger = Trigger.get_code('new_content_permission')
    trigger.send_notification(
            sender=None,
            inbox_type=inbox_type,
            inbox_content_id=content_id,
            inbox_content_type=settings.CONTENT_TYPE_ID(content_type_id),
            content_id=content_id,
            content_type=settings.CONTENT_TYPE_ID(content_type_id),
            account_list=account_id_list,
            is_dashboard=trigger.is_dashboard
    )



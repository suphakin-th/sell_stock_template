from celery import shared_task
from django.conf import settings
from rest_framework import status

from event.models import Event
from log.models import Log
from notification_template.models import Trigger
from transaction.models import Transaction
from utils.content_v2 import get_content
from .models import Inbox


def is_ignore_to_send_notification_email(content_type, progress):
    _content_material_plus_list = [
        settings.CONTENT_TYPE(_code).id for _code in ('activity.activity', 'survey.survey', 'exam.exam')
    ]
    is_standalone = getattr(progress, 'slot_id', None) is None
    is_content_material_plus = content_type.id in _content_material_plus_list
    return is_content_material_plus and not is_standalone


@shared_task(bind=True, queue='user')
def task_push_progress_completed(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    if is_ignore_to_send_notification_email(_content_type, progress):
        return 'Material Plush with slot not need to send email'

    name = getattr(content, 'name_content', None) or content.name
    if content:
        title = 'Congratulations! You have completed this %s' % name
    else:
        title = 'Congratulations! You have completed this %s' % _content_type.app_label

    if len(title) >= 140:
        title = '%s...' % title[:135]

    body = ''
    inbox_type = 20

    account_list = [progress.account]
    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=progress_content_type,
        content_id=progress.id,
    )

    trigger = Trigger.get_code('complete_con')
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
def task_push_progress_failed(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    if is_ignore_to_send_notification_email(_content_type, progress):
        return 'Material Plush with slot not need to send email'
    if content:
        title = 'Sorry, you have failed this %s.!' % content.name
    else:
        title = 'Sorry, you have failed this %s.!' % _content_type.app_label

    body = ''
    inbox_type = 21

    # TODO: Check Integration KPG
    # is_send_complete = Config.pull_value('kpg-send-complete')
    # if is_send_complete:
    #     if transaction.content_type == settings.CONTENT_TYPE('course.course'):
    #         progress = transaction.progresscourse_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('exam.exam'):
    #         progress = transaction.progressexam_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('onboard.onboard'):
    #         progress = transaction.progressonboard_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('event.event'):
    #         progress = transaction.progressevent_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('activity.activity'):
    #         progress = transaction.progressactivity_set.first()
    #     else:
    #         progress = None

    # inbox.send_notification('fail_con')
    account_list = [progress.account]
    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=progress_content_type,
        content_id=progress.id,
    )

    trigger = Trigger.get_code('fail_con')
    if trigger:
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
    else:
        Log.push(None, 'NOTIFICATION_TEMPLATE', 'TRIGGER', None, 'Trigger fail_con not found', status.HTTP_404_NOT_FOUND)


@shared_task(bind=True, queue='user')
def task_push_progress_verifying(self, content_type_id, progress_id):
    progress_content_type = settings.CONTENT_TYPE_ID(content_type_id)
    progress = progress_content_type.model_class()._pull_id(progress_id)
    _content_type, content = get_content(progress_content_type.id, progress.id)
    if is_ignore_to_send_notification_email(_content_type, progress):
        return 'Material Plush with slot not need to send email'
    title = 'Please wait, You are in a verifying process'
    body = ''
    inbox_type = 22

    account_list = [progress.account]
    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=progress_content_type,
        content_id=progress.id,
    )

    trigger = Trigger.get_code('verify_con')
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
def task_push_progress_expired(self, transaction_id):
    transaction = Transaction.pull(transaction_id)
    _, content = get_content(transaction.content_type_id, transaction.content_id)
    if content:
        if isinstance(content, Event):
            event_program_name = content.event_program.name if content.event_program else ''
            title = 'Sorry, this %s (%s) has expired' % (event_program_name, content.name)
        else:
            title = 'Sorry, this %s has expired' % content.name
    else:
        title = 'Sorry, this %s has expired' % transaction.content_type.app_label

    sender = None
    body = ''
    detail = ''

    # TODO: Check Integration KPG
    # is_send_complete = Config.pull_value('kpg-send-complete')
    # if is_send_complete:
    #     if transaction.content_type == settings.CONTENT_TYPE('course.course'):
    #         progress = transaction.progresscourse_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('exam.exam'):
    #         progress = transaction.progressexam_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('onboard.onboard'):
    #         progress = transaction.progressonboard_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('event.event'):
    #         progress = transaction.progressevent_set.first()
    #     elif transaction.content_type == settings.CONTENT_TYPE('activity.activity'):
    #         progress = transaction.progressactivity_set.first()
    #     else:
    #         progress = None

    account_list = [transaction.account]
    trigger = Trigger.get_code('expired_con')
    trigger.send_notification(
        sender=None,
        inbox_type=23,
        inbox_content_type=settings.CONTENT_TYPE('transaction.transaction'),
        inbox_content_id=transaction.id,
        content_id=transaction.content_id,
        content_type=transaction.content_type,
        title=title,
        body=body,
        account_list=account_list
    )

from celery import shared_task
from django.conf import settings

from account.models import Account
from check_in.models import CheckIn
from notification_template.models import Trigger
from progress_event.models import ProgressEvent


@shared_task(bind=True, queue='user')
def task_push_check_in_complete(self, check_in_id, account_admin_id, progress_event_id):
    check_in = CheckIn.pull(check_in_id)
    account_admin = Account.pull(account_admin_id)
    progress_event = ProgressEvent._pull_id(progress_event_id)
    event_content_type = settings.CONTENT_TYPE('event.event')
    title = 'Congratulations, You have successfully checked in'
    body = ''


    account_list = [progress_event.account]
    trigger = Trigger.get_code('succ_checkin')
    trigger.send_notification(
        sender=None,
        inbox_type=50,
        inbox_content_type=settings.CONTENT_TYPE('check_in.checkin'),
        inbox_content_id=check_in.id,
        content_id=progress_event.content_id,
        content_type=event_content_type,
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_check_out_complete(self, check_out_id, account_admin_id, progress_event_id):
    check_out = CheckIn.pull(check_out_id)
    account_admin = Account.pull(account_admin_id)
    #transaction = Transaction.pull(transaction_id)
    progress_event = ProgressEvent._pull_id(progress_event_id)
    event_content_type = settings.CONTENT_TYPE('event.event')
    title = 'Congratulations, You have successfully checked out'
    body = ''
    account_list = [progress_event.account]
    trigger = Trigger.get_code('succ_chckout')
    trigger.send_notification(
        sender=None,
        inbox_type=50,
        inbox_content_type=settings.CONTENT_TYPE('check_in.checkin'),
        inbox_content_id=check_out.id,
        content_id=progress_event.content_id,
        content_type=event_content_type,
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_check_in_fail(self, check_in_id, account_admin_id, progress_event_id):
    check_in = CheckIn.pull(check_in_id)
    account_admin = Account.pull(account_admin_id)
    #transaction = Transaction.pull(transaction_id)
    progress_event = ProgressEvent._pull_id(progress_event_id)
    inbox_type = 51
    event_content_type = settings.CONTENT_TYPE('event.event')
    title = 'Sorry, your check in has failed'
    body = ''
    detail = ''
    account_list = [progress_event.account]
    trigger = Trigger.get_code('fail_checkin')
    trigger.send_notification(
        sender=None,
        inbox_type=51,
        inbox_content_type=settings.CONTENT_TYPE('check_in.checkin'),
        inbox_content_id=check_in.id,
        content_id=progress_event.content_id,
        content_type=event_content_type,
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_check_out_fail(self, check_in_id, account_admin_id, progress_event_id):
    check_in = CheckIn.pull(check_in_id)
    account_admin = Account.pull(account_admin_id)
    #transaction = Transaction.pull(transaction_id)
    progress_event = ProgressEvent._pull_id(progress_event_id)
    event_content_type = settings.CONTENT_TYPE('event.event')

    inbox_type = 51
    title = 'Sorry, your check out has failed'
    body = ''
    detail = ''
    account_list = [progress_event.account]
    trigger = Trigger.get_code('fail_chckout')
    trigger.send_notification(
        sender=None,
        inbox_type=51,
        inbox_content_type=settings.CONTENT_TYPE('check_in.checkin'),
        inbox_content_id=check_in.id,
        content_id=progress_event.content_id,
        content_type=event_content_type,
        title=title,
        body=body,
        account_list=account_list
    )

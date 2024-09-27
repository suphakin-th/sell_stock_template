from celery import shared_task
from django.conf import settings

from content_request.models import ContentRequest
from event.models import Event
from notification_template.models import Trigger
from progress_event.models import SessionEnrollment, ProgressEvent
from transaction.models import Transaction
from utils.content import get_content
from learning_content.models import LearningContent
from account.models import Account
from inbox.utils import get_slot_by_progress_event
from inbox.models import Inbox, Member as InboxMember, Content as InboxContent


def is_inbox_exist_and_update(progress_event, slot_id=None):
    inbox_qs = Inbox.objects.filter(
        type=11,
        content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
        content_id=progress_event.content_id,
    )
    if len(inbox_qs) < 1:
        return False
    if inbox_qs[0].slot_id is not None:
        inbox_qs.update(slot_id=slot_id)
    return True


@shared_task(bind=True, queue='user')
def task_push_progress_event_success_job(self, progress_event_id):
    progress_event = ProgressEvent._pull_id(progress_event_id)
    event_content_type = settings.CONTENT_TYPE('event.event')
    event_id = progress_event.content_id
    event = progress_event.content
    content = Event.objects.get(pk=event_id)
    account_id = progress_event.account_id
    account = Account.pull(account_id)
    title = 'Congratulations!, You have successfully enrolled'
    body = '%s' % content.name
    detail = '.'
    sender = None
    slot_id = get_slot_by_progress_event(progress_event)
    is_inbox_exist_and_update(progress_event, slot_id)
    is_enroll_by_session = event.get_is_session_enrollment()
    # if is_inbox_exist_and_update(progress_event, slot_id) and not is_enroll_by_session:
    #     return
    setattr(content, 'name', content.get_full_name)
    qr_code_holder = content.qr_code_holder
    account_list = [account_id]
    # print('>>send_notifiaction:', progress_event.id)
    if is_enroll_by_session:  # is_reserve
        session_list = SessionEnrollment.pull_list_by_progress(progress_event.id)  # not 0 if after reserve
        if not session_list.exists():  # before
            trigger = Trigger.get_code('enroll_bsess')
            trigger.send_notification(
                sender=None,
                inbox_type=11,
                inbox_content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
                inbox_content_id=progress_event.id,
                content_id=event_id,
                content_type=event_content_type,
                title=title,
                body=body,
                account_list=account_list,
                slot_id=slot_id
            )
        else:  # after
            if qr_code_holder == Event.QR_BY_LEARNER:  # hold by learner
                trigger = Trigger.get_code('enroll_lnaf')
                trigger.send_notification(
                    sender=None,
                    inbox_type=11,
                    inbox_content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
                    inbox_content_id=progress_event.id,
                    content_id=event_id,
                    content_type=event_content_type,
                    title=title,
                    body=body,
                    account_list=account_list,
                    slot_id=slot_id
                )
            else:  # hold by Admin
                trigger = Trigger.get_code('enroll_adaf')
                trigger.send_notification(
                    sender=None,
                    inbox_type=11,
                    inbox_content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
                    inbox_content_id=progress_event.id,
                    content_id=event_id,
                    content_type=event_content_type,
                    title=title,
                    body=body,
                    account_list=account_list,
                    slot_id=slot_id
                )
    else:  # no reserve --> look like after reserve
        if qr_code_holder == Event.QR_BY_LEARNER:  # hold by learner
            trigger = Trigger.get_code('enroll_lnaf')
            trigger.send_notification(
                sender=None,
                inbox_type=11,
                inbox_content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
                inbox_content_id=progress_event.id,
                content_id=event_id,
                content_type=event_content_type,
                title=title,
                body=body,
                account_list=account_list,
                slot_id=slot_id
            )
        else:  # hold by Admin
            trigger = Trigger.get_code('enroll_adaf')
            trigger.send_notification(
                sender=None,
                inbox_type=11,
                inbox_content_type=settings.CONTENT_TYPE('progress_event.progressevent'),
                inbox_content_id=progress_event.id,
                content_id=event_id,
                content_type=event_content_type,
                title=title,
                body=body,
                account_list=account_list,
                slot_id=slot_id
            )

@shared_task(bind=True, queue='user')
def task_push_transaction_success_job(self, transaction_id):
    transaction = Transaction.pull(transaction_id)
    if transaction is None:
        return

    content_request = ContentRequest.pull_by_transaction(transaction)
    if not content_request:
        content = get_content(transaction.content_type_id, transaction.content_id)
        title = 'Congratulations!, You have successfully enrolled'
        if transaction.content_type_id in LearningContent.get_content_type_id_list():
            body = '%s' % content.name_content
        else:
            body = '%s' % content.name
        detail = '.'
        sender = None
        if transaction.content_type_id != settings.CONTENT_TYPE('event.event').id:
            account_list = [transaction.account]
            trigger = Trigger.get_code('enroll_nsess')
            trigger.send_notification(
                sender=None,
                inbox_type=11,
                inbox_content_type=settings.CONTENT_TYPE('transaction.transaction'),
                inbox_content_id=transaction.id,
                content_id=transaction.content_id,
                content_type=transaction.content_type,
                title=title,
                body=body,
                account_list=account_list
            )


@shared_task(bind=True, queue='user')
def task_push_transaction_reject(self, transaction_id):
    transaction = Transaction.pull(transaction_id)
    content = get_content(transaction.content_type_id, transaction.content_id)
    title = 'Sorry, You have been rejected from this %s' % content.name
    body = '%s' % content.name
    detail = ''
    sender = None

    account_list = [transaction.account]
    trigger = Trigger.get_code('reject_enr')
    trigger.send_notification(
        sender=None,
        inbox_type=12,
        inbox_content_type=settings.CONTENT_TYPE('transaction.transaction'),
        inbox_content_id=transaction.id,
        content_id=transaction.content_id,
        content_type=transaction.content_type,
        title=title,
        body=body,
        account_list=account_list
    )

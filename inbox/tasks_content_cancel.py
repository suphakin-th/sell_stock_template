from celery import shared_task
from django.conf import settings
from transaction.models import Transaction
from notification_template.models import Trigger
from utils.content import get_content
from utils.content_type import get_content_type_name


@shared_task(bind=True, queue='user')
def task_push_cancel(self, transaction_id, account_list, is_dashboard,is_approve, account_full_name=''):
    transaction = Transaction.pull(transaction_id)
    if transaction is None:
        return

    content = get_content(transaction.content_type_id, transaction.content_id)
    title = '%s' % content.name
    if is_dashboard:
        body = 'Your team member has canceled %s' % get_content_type_name(transaction.content_type_id)
        trigger = Trigger.get_code('cancel_content_dashboard')
    else:
        body = 'You have successfully canceled %s' % get_content_type_name(transaction.content_type_id)
        trigger = Trigger.get_code('cancel_content_user')
    trigger.send_notification(
        sender=None,
        inbox_type=32,
        inbox_content_type=transaction.content_type,
        inbox_content_id=transaction.content_id,
        content_type=transaction.content_type,
        content_id=transaction.content_id,
        title=title,
        body=body,
        account_list=account_list,
        account_full_name=account_full_name,
        is_approve=is_approve,
        is_dashboard=trigger.is_dashboard
    )

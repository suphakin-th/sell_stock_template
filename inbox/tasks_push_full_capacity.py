from celery import shared_task

from notification_template.models import Trigger
from transaction.models import Transaction
from inbox.utils import get_dashboard_receive_account_id_list


@shared_task(bind=True, queue='dashboard')
def task_push_full_capacity_notification_dashboard(self, content_id, content_type_id):
    transaction = Transaction.objects.filter(
            content_type_id=content_type_id,
            content_id=content_id
        ).first()
    account_id_list = get_dashboard_receive_account_id_list(content_type_id, content_id)
    trigger = Trigger.get_code('full_capacity')
    trigger.send_notification(
        sender=None,
        inbox_type=33,
        inbox_content_type=transaction.content_type,
        inbox_content_id=content_id,
        content_id=content_id,
        content_type=transaction.content_type,
        account_list=account_id_list,
        is_dashboard=trigger.is_dashboard,
    )
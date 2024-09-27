from celery import shared_task
from django.conf import settings

from account.models import IdentityVerification
from notification_template.models import Trigger
from .models import Inbox


@shared_task(bind=True, queue='user')
def task_push_email_verification(self, token):
    identity = IdentityVerification.objects.filter(token=token).first()
    if identity is None:
        return None

    IdentityVerification.objects.filter(account_id=identity.account.id, status=1).exclude(id=identity.id).update(status=3)

    # inbox = Inbox.push(
    #     sender=None,
    #     inbox_type=100,
    #     inbox_content_id=identity.id,
    #     inbox_content_type=settings.CONTENT_TYPE('account.identityverification'),
    #     title='',
    #     body='',
    #     account=identity.account
    # )
    # inbox.send_notification()
    account_list = [identity.account]
    trigger = Trigger.get_code('verification')
    trigger.send_notification(
        sender=None,
        inbox_type=100,
        inbox_content_id=identity.id,
        inbox_content_type=settings.CONTENT_TYPE('account.identityverification'),
        title='',
        body='',
        account_list=account_list
    )

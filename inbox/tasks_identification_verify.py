from celery import shared_task
from django.conf import settings

from notification_template.models import Trigger
from identification.models import Revision, RevisionAccount


@shared_task(bind=True, queue='dashboard')
def task_push_identification_revision_account_verify(self, revision_id, revision_account_id):
    revision = Revision.objects.filter(id=revision_id).first()
    revision_account = RevisionAccount.objects.filter(id=revision_account_id).first()
    inbox_type = 201
    title = ''
    body = ''

    account_list = revision.notification_account_list.split(',') if revision.notification_account_list else []
    if account_list:
        account_list = list(map(int, account_list))
    trigger = Trigger.get_code('verify_identification_photo')

    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=settings.CONTENT_TYPE('identification.revisionaccount'),
        inbox_content_id=revision_account.id,
        content_id=revision.id,
        content_type=settings.CONTENT_TYPE('identification.revision'),
        title=title,
        body=body,
        account_list=account_list,
        is_dashboard=True,
    )


@shared_task(bind=True, queue='user')
def task_push_identification_revision_account_verify_user(self, revision_account_id):
    revision_account = RevisionAccount.objects.filter(id=revision_account_id).first()
    inbox_type = 202
    title = 'Congratulation!, You have been verifyed photo.'
    body = ''

    if revision_account:
        account_list = [revision_account.account_id]
    trigger = Trigger.get_code('verify_identification_photo_user')

    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=settings.CONTENT_TYPE('identification.revisionaccount'),
        inbox_content_id=revision_account.id,
        content_id=revision_account.id,
        content_type=settings.CONTENT_TYPE('identification.revisionaccount'),
        title=title,
        body=body,
        account_list=account_list,
        is_dashboard=False,
    )

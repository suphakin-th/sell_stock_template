from celery import shared_task
from django.conf import settings

from notification_template.models import Trigger
from suggestion.models import Member, Content


@shared_task(bind=True, queue='user')
def task_push_suggestion(self, suggestion_id):
    member_list = Member.objects.filter(suggestion_id=suggestion_id).values_list('account_id', flat=True)
    content_list = Content.objects.filter(suggestion_id=suggestion_id).values('content_id', 'content_type_id')
    if member_list is None:
        return None

    trigger = Trigger.get_code('sug_con')
    trigger.send_notification(
        sender=None,
        inbox_type=9,
        inbox_content_id=suggestion_id,
        inbox_content_type=settings.CONTENT_TYPE('suggestion.suggestion'),
        account_list=member_list,
        content_list=list(content_list)
    )

    return list(member_list)

from celery import shared_task
from django.conf import settings

from account.models import Account
from assignment.models import Round
from config.models import Config
from event.models import Event
from notification_template.models import Trigger
from .models import Inbox
from django.db.models.query import QuerySet


@shared_task(bind=True, queue='user')
def task_push_assignment_job(self, round_id):
    round = Round.objects.filter(id=round_id).first()
    if round is None:
        return None

    title = 'You received new assignment!'
    body = ''
    detail = 'Please click on the link to see more details.\nThank you.'
    sender = round.assignment.account

    account_dict = {}

    # Remove result content type class program
    result_round_queryset = round.result_set.filter(status__in=[1, 3]).exclude(
        content_type_id=settings.CONTENT_TYPE('event_program.eventprogram').id
    )

    for result in result_round_queryset:
        if result.account_id not in account_dict:
            account_dict[result.account_id] = []
        account_dict[result.account_id].append({
            'content_id': result.assigned_content_id,
            'content_type_id': result.content_type_id
        })

    account_list = Account.objects.filter(id__in=account_dict.keys())
    for account in account_list:
        content_list = account_dict[account.id]
        is_event = False
        for content in content_list:
            content_id = content.get('content_id')
            if content['content_type_id'] == settings.CONTENT_TYPE('event.event').id:
                event = Event.pull(content_id)
                if event:
                    is_event = True
                    trigger = Trigger.get_code('assign_sess')
                    trigger.send_notification(
                        sender=None,
                        inbox_type=10,
                        inbox_content_id=round.id,
                        inbox_content_type=settings.CONTENT_TYPE('assignment.round'),
                        title=title,
                        body=body,
                        account_list=[account],
                        content_list=content_list
                    )
                break
        if not is_event:
            trigger = Trigger.get_code('assign_nsess')
            trigger.send_notification(
                sender=None,
                inbox_type=10,
                inbox_content_id=round.id,
                inbox_content_type=settings.CONTENT_TYPE('assignment.round'),
                title=title,
                body=body,
                account_list=[account],
                content_list=content_list
            )

    return account_dict

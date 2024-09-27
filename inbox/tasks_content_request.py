from celery import shared_task
from django.conf import settings

from config.models import Config
from content_request.models import ContentRequest
from notification_template.models import Trigger
from organization.models import Organization
from progress_content_request.models import ProgressStep
from progress_public_learning.models import ProgressPublicLearning
from utils.content import get_content
from .models import Inbox


def push_inbox(content_request, title, account_id_list, inbox_type, trigger_code):
    content = get_content(content_request.content_type_id, content_request.content_id)
    content_type = settings.CONTENT_TYPE('content_request.contentrequest')

    if content.content_type['id'] != settings.CONTENT_TYPE('public_learning.publiclearning').id \
            and inbox_type in [72, 75, 76, 77, 78, 79] and hasattr(content, 'created_from') and content.created_from == 0:
        content_type = settings.CONTENT_TYPE_ID(content.content_type['id'])
        content_id = content.id
    else:
        content_type = settings.CONTENT_TYPE('content_request.contentrequest')
        content_id = content_request.id

    if content.content_type['id'] == settings.CONTENT_TYPE('event.event').id:
        event_program_name = content.event_program.name if content.event_program else ''
        body = '%s (%s)' % (event_program_name, content.name)
    else:
        body = '%s' % content.name

    detail = '.'
    sender = None
    # inbox = Inbox.push(
    #     sender=sender,
    #     inbox_type=inbox_type,
    #     inbox_content_type=content_request.content_type,
    #     inbox_content_id=content_request.id,
    #     content_id=content_id,
    #     content_type=content_type,
    #     account_list=account_id_list,
    #     title=title,
    #     body=body,
    #     detail=detail
    # )
    # inbox.send_notification(trigger_code)
    trigger = Trigger.get_code(trigger_code)
    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=content_request.content_type,
        inbox_content_id=content_request.id,
        content_id=content_id,
        content_type=content_type,
        title=title,
        body=body,
        account_list=account_id_list
    )
    if trigger_code in ['req_reject', 'req_expired', 'req_cancel_a']:
        # supervisor_account_id_list = Organization.objects.filter(
        #     account_id__in=account_id_list
        # ).values_list('parent_id', flat=True)

        organization_qs = Organization.objects.filter(
            account_id__in=account_id_list
        ).select_related('parent', 'account')
        for organization in organization_qs:
            trigger = Trigger.get_code(trigger_code)
            trigger.send_notification(
                sender=None,
                inbox_type=inbox_type,
                inbox_content_type=content_request.content_type,
                inbox_content_id=content_request.id,
                content_id=content_id,
                content_type=content_type,
                title=title,
                body=body,
                account_list=[organization.parent_id],
                prefix_subject='(CC Notification: %s) ' % organization.account.get_full_name()
            )
        # trigger = Trigger.get_code(trigger_code)
        # trigger.send_notification(
        #     sender=None,
        #     inbox_type=inbox_type,
        #     inbox_content_type=content_request.content_type,
        #     inbox_content_id=content_request.id,
        #     content_id=content_id,
        #     content_type=content_type,
        #     title=title,
        #     body=body,
        #     account_list=supervisor_account_id_list,
        #     prefix_subject='(CC Notification) '
        # )



@shared_task(bind=True, queue='user')
def task_push_to_learner(self, content_request_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    title = 'You are in learner list'
    push_inbox(content_request,
               title,
               account_id_list,
               70,
               'learner_noti')


@shared_task(bind=True, queue='user_priority')
def task_push_to_supervisor(self, content_request_id, account_id_list):
    if Config.pull_value('config-is-enable-supervisor-email'):
        content_request = ContentRequest.pull(content_request_id)
        title = 'Your team member are in learner list of the public request'
        push_inbox(content_request,
                   title,
                   account_id_list,
                   73,
                   'super_noti')


@shared_task(bind=True, queue='user_priority')
def task_push_to_approval(self, content_request_id, progress_step_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    progress_step = ProgressStep.objects.filter(id=progress_step_id).first()
    if content_request is None and progress_step is None:
        return None
    # account_id_list = progress_step.account_set.values_list('account_id', flat=True).all()
    title = 'Request for your approval'
    push_inbox(content_request,
               title,
               account_id_list,
               71,
               'req_approve')


@shared_task(bind=True, queue='user')
def task_push_to_kms_approval(self, content_request_id, progress_step_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    progress_step = ProgressStep.objects.filter(id=progress_step_id).first()
    if content_request is None and progress_step is None:
        return None

    title = 'Request for Create Material'
    push_inbox(content_request,
               title,
               account_id_list,
               80,
               'req_creator_approve')


# Step

@shared_task(bind=True, queue='user_priority')
def task_push_result_step_complete(self, content_request_id, count_step_complete, count_step):
    content_request = ContentRequest.pull(content_request_id)
    account_id_list = [content_request.account_id] + list(
        content_request.content_request_account.values_list('account_id', flat=True))
    account_id_list = list(dict.fromkeys(account_id_list))
    title = 'Congratulations! Your request has been approved for step %s/%s' % (
        count_step_complete,
        count_step
    )
    push_inbox(content_request,
               title,
               account_id_list,
               72,
               'approve_step')


# Result


@shared_task(bind=True, queue='user_priority')
def task_push_result_complete(self, content_request_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    # account_id_list = [content_request.account_id]
    title = 'Congratulations! Your request has been approved for all steps.'
    push_inbox(content_request,
               title,
               account_id_list,
               75,
               'approve_comp')


@shared_task(bind=True, queue='user_priority')
def task_push_result_reject(self, content_request_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    # account_id_list = [content_request.account_id]
    title = 'Sorry, Your request has been rejected.'
    push_inbox(content_request,
               title,
               account_id_list,
               76,
               'req_reject')


@shared_task(bind=True, queue='user_priority')
def task_push_result_expired(self, content_request_id, account_id_list):
    content_request = ContentRequest.pull(content_request_id)
    # account_id_list = [content_request.account_id]
    title = 'Sorry, Your request has expired.'
    push_inbox(content_request,
               title,
               account_id_list,
               77,
               'req_expired')


@shared_task(bind=True, queue='user_priority')
def task_push_result_cancel(self, content_request_id):
    content_request = ContentRequest.pull(content_request_id)
    account_id_list = [content_request.account_id] + list(
        content_request.content_request_account.values_list('account_id', flat=True))
    account_id_list = list(dict.fromkeys(account_id_list))
    title = 'Sorry, Your request has been canceled by requester'
    push_inbox(content_request,
               title,
               account_id_list,
               78,
               'req_cancel_r')


@shared_task(bind=True, queue='user_priority')
def task_push_result_cancel_by_admin(self, content_request_id):
    content_request = ContentRequest.pull(content_request_id)
    account_id_list = [content_request.account_id] + list(
        content_request.content_request_account.values_list('account_id', flat=True))
    account_id_list = list(dict.fromkeys(account_id_list))
    title = 'Sorry, Your request has been canceled by administrator'
    push_inbox(content_request,
               title,
               account_id_list,
               79,
               'req_cancel_a')


@shared_task(bind=True, queue='dashboard')
def task_verify_learning_result(self, progress_public_learning_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()
    supervisor = Organization.objects.filter(account_id=progress_public_learning.account_id).first()
    trigger = Trigger.get_code('verify_learning_result')
    trigger.send_notification(
        sender=None,
        inbox_type=121,
        inbox_content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        inbox_content_id=progress_public_learning_id,
        content_id=progress_public_learning_id,
        content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        account_list=[supervisor.parent] if supervisor and supervisor.parent else [],
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='dashboard')
def task_learning_result_status_failed_autocompleted(self, progress_public_learning_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()
    supervisor = Organization.objects.filter(account_id=progress_public_learning.account_id).first()
    trigger = Trigger.get_code('learning_result_autocompleted_failed_admin')
    trigger.send_notification(
        sender=None,
        inbox_type=124,
        inbox_content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        inbox_content_id=progress_public_learning_id,
        content_id=progress_public_learning_id,
        content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        account_list=[supervisor.parent] if supervisor and supervisor.parent else [],
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='user')
def task_learning_result_status_failed_autocompleted_user(self, progress_public_learning_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()

    content_request = ContentRequest.objects.filter(
        content_type_id=settings.CONTENT_TYPE('public_learning.publiclearning').id,
        content_id=progress_public_learning.public_learning_id).first()

    trigger = Trigger.get_code('learning_result_autocompleted_failed_user')
    account = [progress_public_learning.account_id] if progress_public_learning.account_id else []
    trigger.send_notification(
        sender=None,
        inbox_type=125,
        inbox_content_type=settings.CONTENT_TYPE('content_request.contentrequest'),
        inbox_content_id=content_request.id,
        content_id=content_request.id,
        content_type=settings.CONTENT_TYPE('content_request.contentrequest'),
        account_list=account,
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='dashboard')
def task_learning_result_status_completed_autocompleted(self, progress_public_learning_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()
    supervisor = Organization.objects.filter(account_id=progress_public_learning.account_id).first()
    trigger = Trigger.get_code('learning_result_autocompleted_completed_admin')
    trigger.send_notification(
        sender=None,
        inbox_type=122,
        inbox_content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        inbox_content_id=progress_public_learning_id,
        content_id=progress_public_learning_id,
        content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        account_list=[supervisor.parent] if supervisor and supervisor.parent else [],
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='user')
def task_learning_result_status_completed_autocompleted_user(self, progress_public_learning_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()

    content_request = ContentRequest.objects.filter(
        content_type_id=settings.CONTENT_TYPE('public_learning.publiclearning').id,
        content_id=progress_public_learning.public_learning_id).first()

    trigger = Trigger.get_code('learning_result_autocompleted_completed_user')
    account = [progress_public_learning.account_id] if progress_public_learning.account_id else []
    trigger.send_notification(
        sender=None,
        inbox_type=123,
        inbox_content_type=settings.CONTENT_TYPE('content_request.contentrequest'),
        inbox_content_id=content_request.id,
        content_id=content_request.id,
        content_type=settings.CONTENT_TYPE('content_request.contentrequest'),
        account_list=account,
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='dashboard')
def task_push_update_learning_result(self, progress_public_learning_id, updated_account_id):
    progress_public_learning = ProgressPublicLearning.objects.filter(id=progress_public_learning_id).first()
    account_id_list = progress_public_learning.get_updated_account_id_list()
    account_id_list = account_id_list.exclude(updated_account_id=updated_account_id) if updated_account_id in account_id_list else account_id_list
    trigger = Trigger.get_code('update_learning_result_status_admin')
    trigger.send_notification(
        sender=None,
        inbox_type=126,
        inbox_content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        inbox_content_id=progress_public_learning_id,
        content_id=progress_public_learning_id,
        content_type=settings.CONTENT_TYPE('public_learning.publicrequest'),
        account_list=account_id_list,
        is_dashboard=trigger.is_dashboard,
    )

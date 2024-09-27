import datetime
from datetime import timedelta
from django.conf import settings
from celery import shared_task

from .models import Inbox
from config.models import Config
from playlist.models import Playlist, AssignmentAccount, Assignment as PlaylistAssignment, \
Account as PlaylistAccount, RequestContent, Content as PlaylistContent
from progress_playlist.models import ProgressPlaylist
from notification_template.models import Trigger


@shared_task(bind=True, queue='user')
def task_push_result_learning_playlist_created(self, content_id, account_id_list):
    title = 'New Learning Playlist has been created'

    body = ''
    inbox_type = 190

    account_list = account_id_list
    playlist = Playlist.pull(content_id)

    if playlist.created_by.id in account_list:
        return
    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=settings.CONTENT_TYPE('playlist.playlist'),
        content_id=content_id,
    )
    if inbox_qs.exists():
        return
    trigger = Trigger.get_code('playlist_new')
    trigger.send_notification(
        sender=None,
        inbox_type=inbox_type,
        inbox_content_type=settings.CONTENT_TYPE('playlist.playlist'),
        inbox_content_id=content_id,
        content_id=content_id,
        content_type=settings.CONTENT_TYPE('playlist.playlist'),
        title=title,
        body=body,
        account_list=account_list
    )


@shared_task(bind=True, queue='user')
def task_push_result_learning_playlist_assignment(self, assignment_id):
    title = 'New Learning Playlist Assignment'

    body = ''
    inbox_type = 191

    inbox_qs = Inbox.objects.filter(
        type=inbox_type,
        content_type=settings.CONTENT_TYPE('playlist.assignment'),
        content_id=assignment_id,
    )
    if inbox_qs.exists():
        return
    assignment = PlaylistAssignment.pull(assignment_id)
    assignment_accounts = AssignmentAccount.objects.filter(
        assignment_id=assignment_id
    )
    playlist = Playlist.pull(assignment.playlist_id)
    if playlist is None:
        return
    for assignment_account in assignment_accounts:
        count_assign = AssignmentAccount.objects.filter(
                assignment__playlist_id=assignment.playlist_id,
                account_id=assignment_account.account_id,
                status_result__in=[1, 3]
        ).count()

        if assignment_account.account != assignment.assignee_account and count_assign == 1:
            trigger = Trigger.get_code('playlist_assign')
            trigger.send_notification(
                sender=None,
                inbox_type=inbox_type,
                inbox_content_type=settings.CONTENT_TYPE('playlist.assignment'),
                inbox_content_id=assignment_id,
                content_id=playlist.id,
                content_type=settings.CONTENT_TYPE('playlist.playlist'),
                title=title,
                body=body,
                account_list=[assignment_account.account]
            )

@shared_task(bind=True, queue='user')
def task_push_result_learning_playlist_content_added(self, playlist_id):
    title = 'New Contents Added to Learning Playlist'

    body = ''
    inbox_type = 192
    playlist_noti_time = Config.pull_value('config-learning-playlist-notification-time')
    if playlist_noti_time is None:
        playlist_noti_time = 8
    today = datetime.datetime.now()
    todaytime = today.replace(hour=playlist_noti_time, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(1)
    yesterdaytime = yesterday.replace(hour=playlist_noti_time, minute=0, second=0, microsecond=0)
    playlist_content_accounts = list(PlaylistContent.objects.filter(
                            datetime_create__gt=yesterdaytime,
                            datetime_create__lt=todaytime,
                            is_duplicate=False,
                            playlist_id=playlist_id
                        ).values_list('added_by_id', flat=True))
    playlist_content_account_ids = [account_id for account_id in playlist_content_accounts if account_id]
    playlist_content_account_ids = list(dict.fromkeys(playlist_content_account_ids))
    _playlist_accounts = []
    learner_account_ids = ProgressPlaylist.objects.filter(
        content_id=playlist_id
    ).values_list('account_id', flat=True)
    for account_id in learner_account_ids:
        _playlist_content_account_ids = playlist_content_account_ids
        if account_id in _playlist_content_account_ids:
            _playlist_content_account_ids.remove(account_id)
        if len(_playlist_content_account_ids) > 0:
            trigger = Trigger.get_code('playlist_content')
            trigger.send_notification(
                sender=None,
                inbox_type=inbox_type,
                inbox_content_type=settings.CONTENT_TYPE('playlist.content'),
                inbox_content_id=playlist_id,
                content_id=playlist_id,
                content_type=settings.CONTENT_TYPE('playlist.playlist'),
                title=title,
                body=body,
                account_list=[account_id]
            )


@shared_task(bind=True, queue='user')
def task_push_result_learning_playlist_approval(self, playlist_id):
    title = 'Request for Learning Playlist Approval'

    body = ''
    inbox_type = 193

    playlist_accounts = PlaylistAccount.objects.filter(playlist_id=playlist_id, group_list__code__in=['admin', 'content manager'])
    for playlist_account in playlist_accounts:
        trigger = Trigger.get_code('playlist_app')
        trigger.send_notification(
            sender=None,
            inbox_type=inbox_type,
            inbox_content_type=settings.CONTENT_TYPE('playlist.playlist'),
            inbox_content_id=playlist_id,
            content_id=playlist_id,
            content_type=settings.CONTENT_TYPE('playlist.playlist'),
            title=title,
            body=body,
            account_list=[playlist_account.account]
        )


@shared_task(bind=True, queue='user')
def task_push_result_learning_playlist_recommended(self, playlist_id):
    title = 'New Recommended Contents in Learning Playlist'

    body = ''
    inbox_type = 194

    playlist_accounts = PlaylistAccount.objects.filter(playlist_id=playlist_id, group_list__code__in=['owner'])
    for playlist_account in playlist_accounts:
        trigger = Trigger.get_code('playlist_rec')
        trigger.send_notification(
            sender=None,
            inbox_type=inbox_type,
            inbox_content_type=settings.CONTENT_TYPE('playlist.playlist'),
            inbox_content_id=playlist_id,
            content_id=playlist_id,
            content_type=settings.CONTENT_TYPE('playlist.playlist'),
            title=title,
            body=body,
            account_list=[playlist_account.account]
        )

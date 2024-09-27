from celery import shared_task
from discussion.models import DiscussionBoard, Comment
from inbox.utils import get_dashboard_receive_account_id_list
from instructor.models import Account as InstructorAccount
from notification_template.models import Trigger
from provider.models import Account as ProviderAccount
from transaction.models import Transaction


@shared_task(bind=True, queue='dashboard')
def task_push_discussion_notification_dashboard(self, comment_id):
    comment = Comment.objects.filter(id=comment_id).first()
    discussion = DiscussionBoard.objects.filter(id=comment.content_id).first()
    account_id_list = get_dashboard_receive_account_id_list(discussion.content_type_id, discussion.content_id)
    if comment.parent:
        if comment.parent.author_id != comment.author_id and comment.parent.author_id in account_id_list and comment.parent.author_role in [2, 3, 4, 5]:
            account_id_list = [comment.parent.author_id]
        else:
            account_id_list = []
    if comment.author_id in account_id_list:
        account_id_list.remove(comment.author_id)
    trigger = Trigger.get_code('discussion_board_admin')
    trigger.send_notification(
        sender=None,
        inbox_type=160,
        inbox_content_type=discussion.content_type,
        inbox_content_id=discussion.content_id,
        content_id=discussion.content_id,
        content_type=discussion.content_type,
        account_list=account_id_list,
        content_list=[comment],
        is_dashboard=trigger.is_dashboard,
    )


@shared_task(bind=True, queue='user')
def task_push_discussion_notification_user(self, comment_id):
    comment = Comment.objects.filter(id=comment_id).first()
    discussion = DiscussionBoard.objects.filter(id=comment.content_id).first()
    account_id_list = []
    admin_account_id_list = get_dashboard_receive_account_id_list(discussion.content_type_id, discussion.content_id)
    if not comment.parent and comment.author_role in [2, 3, 4, 5] and comment.author_id in admin_account_id_list:
        account_id_list = Transaction.objects.filter(
            content_type_id=discussion.content_type_id,
            content_id=discussion.content_id,
            status=0).values_list('account_id', flat=True)
    elif comment.parent and comment.parent.author_role == 1:
        if comment.parent.author_id != comment.author_id and (
                (comment.author_role in [2, 3, 4, 5] and comment.author_id in admin_account_id_list) or comment.author_role == 1):
            account_id_list = [comment.parent.author_id]
    if comment.author_id in account_id_list:
        account_id_list.remove(comment.author_id)
    trigger = Trigger.get_code('discussion_board_user')
    trigger.send_notification(
        sender=None,
        inbox_type=161,
        inbox_content_type=discussion.content_type,
        inbox_content_id=discussion.content_id,
        content_id=discussion.content_id,
        content_type=discussion.content_type,
        account_list=account_id_list,
        content_list=[comment],
        is_dashboard=trigger.is_dashboard,
    )

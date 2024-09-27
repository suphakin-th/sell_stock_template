from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from config.models import Config
from event.models import Session as EventSession, Schedule as EventSchedule, Session
from job.models import Scheduler
from mailer.create_ics_file import create_ics_file
from progress_check_in.models import ProgressCheckIn
from progress_event.models import SessionEnrollment, ProgressEvent
from term.models import Rule
from transaction.models import Transaction
from utils.datetime import convert_to_local
from utils.model_permission import VIEW_BY_PERMISSIONS, DEFAULT_PERMISSIONS


class Inbox(models.Model):
    TYPE_CHOICES = (
        # Single message
        (1, 'Direct Message'),
        (2, 'News Update'),

        # Transaction -> Content
        (9, 'Suggestion'),
        (10, 'Assignment'),
        (11, 'Transaction_Success'),
        (12, 'Transaction Reject'),

        # Progress -> Content
        (20, 'Progress Completed'),
        (21, 'Progress Fail'),
        (22, 'Progress Verifying'),
        (23, 'Progress Expired'),

        # Content
        (30, 'Content Start'),
        (31, 'Before Content start'),
        (32, 'Content Cancelled'),
        (33, 'Full Capacity Notification'),
        (34, 'New Content Permission'),


        # Certificate -> Content
        (40, 'Approved Certificate'),
        (41, 'UnApproved Certificate'),
        (42, 'Notify Approve Certificate'),

        # Check in -> content
        (50, 'Check in Complete'),
        (51, 'Check in Fail'),

        # ProgressExam -> Content
        (60, 'Progress Exam Start'),
        (61, 'Progress Exam Announcement'),
        (62, 'Progress Exam Answer Key'),

        # Content Request
        (70, 'Notify Learner'),
        (71, 'Notify Approval'),
        (73, 'Notify Supervisor'),

        (72, 'Notify result step : Approved'),

        (75, 'Notify Result : Complete'),
        (76, 'Notify Result : Rejected'),
        (77, 'Notify Result : Expired'),
        (78, 'Notify Result : Canceled by Requester'),
        (79, 'Notify Result : Canceled by Administrator'),

        (80, 'Notify KMS Approval'),

        # Check out Conference
        (90, 'Class Check Out Conference'),

        # Verification
        (100, ' Verify Email'),

        # --------------------------- Escalation Notification Template P0221: 110-200 ---------------------------
        # 11x Course
        (110, 'Course No Expire'),  # course_noex
        (111, 'Course Expire'),  # course_ex
        # 12x Public Request
        (120, 'Public Request Response'),  # pub_r_res
        (121, 'Public Request Verify Result Admin'),  # verify_learning_result
        (122, 'Learning result status Completed(Auto Completed)'),
        (123, 'Learning result status Completed(Auto Completed) Noti User'),
        (124, 'Learning result status Failed(Auto Completed) Noti Admin'),
        (125, 'Learning result status Failed(Auto Completed) Noti User'),
        (126, 'Public Request Update Status Admin'),
        # 13x Req Material
        (130, 'Request Material No Expired'),  # reqmat_noex
        (131, 'Request Material Expired'),  # reqmat_ex
        # 14x before Class start
        (140, 'before class start qr hold by admin check in'),
        (141, 'before class start qr hold by learner check in'),
        (142, 'reserve class start qr hold by admin'),
        (143, 'reserve class start qr hold by learner'),
        # 15x before live start
        (150, 'before live start'),
        # 16x discussion board
        (160, 'Notify Discussion Admin'),  # discussion_board_admin
        (161, 'Notify Discussion User'),  # discussion_board_user

        # 19x Learning material
        (190, 'Learning Material Created'),
        (191, 'Learning Material Assignment'),
        (192, 'Learning Material Content Added'),
        (193, 'Learning Material Approval'),
        (194, 'Learning Material Recommended'),

        # 20x Identification
        (201, 'Identification Revision Verify'),
        (202, 'Identification Revision Verify User'),
        # 21x before learning path next section start
        (210, 'Before Learning path Next Section start'),
    )

    STATUS_CHOICES = (
        (-2, 'FCM Failed'),
        (-1, 'Failed'),
        (0, 'Draft'),
        (1, 'Sent'),
    )

    account = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)  # Send msg

    type = models.IntegerField(choices=TYPE_CHOICES)
    trigger = models.ForeignKey('notification_template.Trigger', null=True, on_delete=models.SET_NULL)

    title = models.TextField(blank=True)
    body = models.TextField(blank=True)
    detail = models.TextField(blank=True)
    image = models.ImageField(upload_to='inbox/%Y/%m/', null=True, blank=True)

    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, blank=None, null=True)
    content_id = models.PositiveIntegerField(blank=True, null=True)
    slot = models.ForeignKey('slot.Slot', on_delete=models.CASCADE, null=True, default=None)

    is_dashboard = models.BooleanField(default=False, db_index=True)

    count_read = models.IntegerField(default=0)
    count_send = models.IntegerField(default=1)

    status = models.IntegerField(choices=STATUS_CHOICES, default=1)

    datetime_send = models.DateTimeField(null=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    datetime_update = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-datetime_create']
        default_permissions = DEFAULT_PERMISSIONS + VIEW_BY_PERMISSIONS

    def __str__(self):
        return "%s %s" % (self.id, self.get_type_display())

    @property
    def config_fcm(self):
        return Config.pull_value('notification-client-list')

    @property
    def config_mail(self):
        return Config.pull_value('notification-email-list')

    @property
    def is_read(self):
        return self.read_set.filter(inbox=self).exists()

    @property
    def click_action(self):
        from django.conf import settings
        if self.type == 1:
            return 'OPEN_DIRECT_MESSAGE_DETAIL'
        elif self.type == 2:
            return 'OPEN_NEWS_UPDATE_DETAIL'
        elif self.type in [30, 31, 32]:
            if self.content_type == settings.CONTENT_TYPE('event.event'):
                word = 'CLASS'
            else:
                word = self.content_type.app_label.upper()
            return 'OPEN_%s_DETAIL' % word
        else:
            if self.content_type == settings.CONTENT_TYPE('event.event'):
                word = 'CLASS'
            else:
                word = self.content_type.app_label.upper()
            return 'OPEN_%s_DETAIL' % word

    @staticmethod
    def push(sender,
             inbox_type,
             inbox_content_type=None,
             inbox_content_id=None,
             title='',
             body='',
             detail='',
             content_id=None,
             content_type=None,
             content_list=None,
             account=None,
             account_list=None,
             slot_id=None,
             trigger_id=None,
             is_dashboard=False):
        from django.db.models.query import QuerySet
        from account.models import Account
        from .caches import cache_account_count, cache_dashboard_account_count, cache_dashboard_account_count_unread_delete

        _account = account
        if isinstance(sender, int):
            sender = Account.objects.filter(id=sender).first()
        elif isinstance(sender, dict):
            sender_list = sender.values()
            account_id = sender_list.pop(0)
            _account_queryset = Account.objects.filter(id=account_id)
            if _account_queryset.exists():
                _account = _account_queryset.first()
            else:
                _account = None

        else:
            sender = None

        inbox = Inbox.objects.create(
            account=sender,
            type=inbox_type,
            title=title,
            body=body,
            detail=detail,
            status=0,
            content_type=inbox_content_type,
            content_id=inbox_content_id,
            slot_id=slot_id,
            trigger_id=trigger_id,
            is_dashboard=is_dashboard
        )

        # Clear notification
        if sender or _account:
            if is_dashboard:
                count = cache_dashboard_account_count(sender if sender else _account)
                cache_dashboard_account_count_unread_delete(sender if sender else _account)
            else:
                count = cache_account_count(sender if sender else _account)
            count.add()

        if content_id is not None and content_type is not None:
            inbox.content_set.create(content_id=content_id, content_type=content_type)
        if content_list is not None:
            for content in content_list:
                if isinstance(content, dict):
                    content_template = {'content_id': -1,
                                        'content_type_id': -1}
                    if content.keys() == content_template.keys():
                        inbox.content_set.create(**content)
                elif isinstance(content, QuerySet):
                    if hasattr(content, 'content_id') and hasattr(content, 'content_type_id'):
                        inbox.content_set.create(content_id=getattr(content, 'content_id'),
                                                 content_type_id=getattr(content, 'content_type_id'))

        if _account is not None:
            if isinstance(_account, QuerySet):
                inbox.member_set.create(account=_account, is_dashboard=is_dashboard)
            elif isinstance(_account, int):
                inbox.member_set.create(account_id=_account, is_dashboard=is_dashboard)
            elif isinstance(_account, dict):
                _account.update({'is_dashboard': is_dashboard})
                inbox.member_set.create(**_account)
            elif isinstance(_account, Account):
                inbox.member_set.create(account=_account, is_dashboard=is_dashboard)

        if account_list is not None:
            if isinstance(account_list, QuerySet):
                for _account in account_list:
                    if isinstance(_account, dict):
                        account_id = _account.get('account_id', None)
                        if account_id is None:
                            account_id = _account.get('id', None)
                        if account_id is not None:
                            inbox.member_set.get_or_create(account_id=account_id, is_dashboard=is_dashboard)
                    elif hasattr(_account, 'account_id'):
                        inbox.member_set.get_or_create(account_id=getattr(_account, 'account_id'),
                                                       is_dashboard=is_dashboard)
                    elif isinstance(_account, Account):
                        inbox.member_set.get_or_create(account=_account, is_dashboard=is_dashboard)
                    elif isinstance(_account, int):
                        inbox.member_set.get_or_create(account_id=_account, is_dashboard=is_dashboard)
            elif isinstance(account_list, list):
                for account_id in account_list:
                    if isinstance(account_id, int):
                        inbox.member_set.get_or_create(account_id=account_id, is_dashboard=is_dashboard)
                    elif isinstance(account_id, dict):
                        data_template = {'account_id': -1}
                        if account_id.keys() == data_template.keys():
                            inbox.member_set.get_or_create(**account_id, is_dashboard=is_dashboard)
                    elif isinstance(account_id, Account):
                        inbox.member_set.get_or_create(account_id=account_id.id, is_dashboard=is_dashboard)
        return inbox

    @staticmethod
    def push_news_update(news_update, is_queue):
        from .tasks_push_news_update import task_push_news_update
        if is_queue:
            task_push_news_update.delay(news_update.id)
        else:
            task_push_news_update(**{'news_update_id': news_update.id})

    @staticmethod
    def push_news_update_force_send(news_update, is_queue):
        from .tasks_push_news_update import task_push_news_update_force_send
        if is_queue:
            task_push_news_update_force_send.delay(news_update.id)
        else:
            task_push_news_update_force_send(**{'news_update_id': news_update.id})

    @staticmethod
    def push_assignment(round, is_queue):
        from .tasks_push_assignment import task_push_assignment_job
        if is_queue:
            task_push_assignment_job.delay(round.id)
        else:
            task_push_assignment_job(**{'round_id': round.id})

    @staticmethod
    def push_suggestion(suggestion, is_queue, datetime_suggest=None):
        from .tasks_push_suggestion import task_push_suggestion
        if datetime_suggest:
            Scheduler.push(
                'push_suggestion_%s' % suggestion.id,
                task_push_suggestion,
                datetime_suggest,
                suggestion.id
            )
        else:
            if is_queue:
                task_push_suggestion.delay(suggestion.id)
            else:
                task_push_suggestion(**{'suggestion_id': suggestion.id})

    @staticmethod
    def push_progress_exam_announcement(progress_exam, is_queue):
        from .tasks_push_progress_exam import task_push_progress_exam_announcement
        if is_queue:
            task_push_progress_exam_announcement.delay(progress_exam.id)
        else:
            task_push_progress_exam_announcement(**{'progress_exam_id': progress_exam.id})

    @staticmethod
    def push_progress_exam_answer_key(progress_exam, is_queue):
        from .tasks_push_progress_exam import task_push_progress_exam_answer_key
        if is_queue:
            task_push_progress_exam_answer_key.delay(progress_exam.id)
        else:
            task_push_progress_exam_answer_key(**{'progress_exam_id': progress_exam.id})

    @staticmethod
    def push_transaction_progress_event_success(progress_event, is_queue=False):
        from .tasks_push_transaction import task_push_progress_event_success_job
        if is_queue:
            task_push_progress_event_success_job.delay(progress_event_id=progress_event.id)
        else:
            task_push_progress_event_success_job(**{'progress_event_id': progress_event.id})

    @staticmethod
    def push_transaction_success(transaction, is_queue):
        from .tasks_push_transaction import task_push_transaction_success_job
        if is_queue:
            task_push_transaction_success_job.delay(transaction.id)
        else:
            task_push_transaction_success_job(**{'transaction_id': transaction.id})

    @staticmethod
    def push_transaction_reject(transaction, is_queue):
        from .tasks_push_transaction import task_push_transaction_reject
        if is_queue:
            task_push_transaction_reject.delay(transaction.id)
        else:
            task_push_transaction_reject(**{'transaction_id': transaction.id})

    @staticmethod
    def push_progress_completed(progress, is_queue):
        from .tasks_push_progress import task_push_progress_completed
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_progress_completed.delay(progress_content_type.id, progress.id)
        else:
            task_push_progress_completed(**{'content_type_id': progress_content_type.id, 'progress_id': progress.id})

    @staticmethod
    def push_progress_failed(progress, is_queue):
        from .tasks_push_progress import task_push_progress_failed
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_progress_failed.delay(progress_content_type.id, progress.id)
        else:
            task_push_progress_failed(**{'content_type_id': progress_content_type.id, 'progress_id': progress.id})

    @staticmethod
    def push_progress_verifying(progress, is_queue):
        from .tasks_push_progress import task_push_progress_verifying
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_progress_verifying.delay(progress_content_type.id, progress.id)
        else:
            task_push_progress_verifying(**{'content_type_id': progress_content_type.id, 'progress_id': progress.id})

    @staticmethod
    def push_progress_expired(transaction, is_queue):
        from .tasks_push_progress import task_push_progress_expired
        if is_queue:
            task_push_progress_expired.delay(transaction.id)
        else:
            task_push_progress_expired(**{'transaction_id': transaction.id})

    @staticmethod
    def push_content_start(inbox_type, title, content_type_id, content_id, is_queue):
        from .tasks_push_content import task_push_content_start
        if is_queue:
            task_push_content_start.delay(inbox_type, title, content_type_id, content_id)
        else:
            task_push_content_start.apply(
                kwargs={'inbox_type': inbox_type,
                        'title': title,
                        'content_type_id': content_type_id,
                        'content_id': content_id})

    @staticmethod
    def push_content_cancelled(content_type_id, content_id, is_queue):
        from .tasks_push_content import task_push_content_cancelled
        if is_queue:
            task_push_content_cancelled.delay(content_type_id, content_id)
        else:
            task_push_content_cancelled.apply(content_type_id, content_id)

    @staticmethod
    def push_approve_certificate(progress, is_queue):
        from .tasks_push_certificate import task_push_approve_certificate
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_approve_certificate.delay(progress_content_type.id, progress.id)
        else:
            task_push_approve_certificate(**{
                'content_type_id': progress_content_type.id, 'progress_id': progress.id
            })

    @staticmethod
    def push_unapproved_certificate(progress, is_queue):
        from .tasks_push_certificate import task_push_unapproved_certificate
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_unapproved_certificate.delay(progress_content_type.id, progress.id)
        else:
            task_push_unapproved_certificate(**{
                'content_type_id': progress_content_type.id, 'progress_id': progress.id
            })

    @staticmethod
    def push_check_in_complete(check_in, account_admin, progress_event, is_queue):
        from .tasks_push_check_in import task_push_check_in_complete
        if is_queue:
            task_push_check_in_complete.delay(check_in.id, account_admin.id, progress_event.id)
        else:
            task_push_check_in_complete(**{
                'check_in_id': check_in.id,
                'account_admin_id': account_admin.id,
                'progress_event_id': progress_event.id})

    @staticmethod
    def push_check_out_complete(check_out, account_admin, progress_event, is_queue):
        from .tasks_push_check_in import task_push_check_out_complete
        if is_queue:
            task_push_check_out_complete.delay(check_out.id, account_admin.id, progress_event.id)
        else:
            task_push_check_out_complete(**{
                'check_out_id': check_out.id,
                'account_admin_id': account_admin.id,
                'progress_event_id': progress_event.id})

    @staticmethod
    def push_check_in_fail(check_in, account_admin, progress_event, is_queue):
        from .tasks_push_check_in import task_push_check_in_fail
        if is_queue:
            task_push_check_in_fail.delay(check_in.id, account_admin.id, progress_event.id)
        else:
            task_push_check_in_fail(**{
                'check_in_id': check_in.id,
                'account_admin_id': account_admin.id,
                'progress_event_id': progress_event.id})

    @staticmethod
    def push_check_out_fail(check_in, account_admin, progress_event, is_queue):
        from .tasks_push_check_in import task_push_check_out_fail
        if is_queue:
            task_push_check_out_fail.delay(check_in.id, account_admin.id, progress_event.id)
        else:
            task_push_check_out_fail(**{
                'check_in_id': check_in.id,
                'account_admin_id': account_admin.id,
                'progress_event_id': progress_event.id})

    @staticmethod
    def push_to_learner(content_request, account_id_list, is_queue):
        from .tasks_content_request import task_push_to_learner
        if is_queue:
            task_push_to_learner.delay(content_request.id, account_id_list)
        else:
            task_push_to_learner(**{
                'content_request_id': content_request.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_to_supervisor(content_request, account_id_list, is_queue):
        from .tasks_content_request import task_push_to_supervisor
        if is_queue:
            task_push_to_supervisor.delay(content_request.id, account_id_list)
        else:
            task_push_to_supervisor(**{
                'content_request_id': content_request.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_to_approval(content_request, progress_step, account_id_list, is_queue):
        from .tasks_content_request import task_push_to_approval
        if is_queue:
            task_push_to_approval.delay(content_request.id, progress_step.id, account_id_list)
        else:
            task_push_to_approval(**{
                'content_request_id': content_request.id,
                'progress_step_id': progress_step.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_to_kms_approval(content_request, progress_step, account_id_list, is_queue):
        from .tasks_content_request import task_push_to_kms_approval
        if is_queue:
            task_push_to_kms_approval.delay(content_request.id, progress_step.id, account_id_list)
        else:
            task_push_to_kms_approval(**{
                'content_request_id': content_request.id,
                'progress_step_id': progress_step.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_result_step_complete(progress_content_request, is_queue):
        from .tasks_content_request import task_push_result_step_complete
        if is_queue:
            task_push_result_step_complete.delay(
                progress_content_request.content_request.id,
                progress_content_request.count_step_complete,
                progress_content_request.count_step
            )
        else:
            task_push_result_step_complete(**{
                'content_request_id': progress_content_request.content_request.id,
                'count_step_complete': progress_content_request.count_step_complete,
                'count_step': progress_content_request.count_step
            })

    @staticmethod
    def push_result_complete(content_request, account_id_list, is_queue):
        from .tasks_content_request import task_push_result_complete
        if is_queue:
            task_push_result_complete.delay(content_request.id, account_id_list)
        else:
            task_push_result_complete(**{
                'content_request_id': content_request.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_result_reject(content_request, account_id_list, is_queue):
        from .tasks_content_request import task_push_result_reject
        if is_queue:
            task_push_result_reject.delay(content_request.id, account_id_list)
        else:
            task_push_result_reject(**{
                'content_request_id': content_request.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_result_expired(content_request, account_id_list, is_queue):
        from .tasks_content_request import task_push_result_expired
        if is_queue:
            task_push_result_expired.delay(content_request.id, account_id_list)
        else:
            task_push_result_expired(**{
                'content_request_id': content_request.id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_result_cancel(content_request, is_queue):
        from .tasks_content_request import task_push_result_cancel
        if is_queue:
            task_push_result_cancel.delay(content_request.id)
        else:
            task_push_result_cancel(**{
                'content_request_id': content_request.id
            })

    @staticmethod
    def push_result_cancel_by_admin(content_request, is_queue):
        from .tasks_content_request import task_push_result_cancel_by_admin
        if is_queue:
            task_push_result_cancel_by_admin.delay(content_request.id)
        else:
            task_push_result_cancel_by_admin(**{
                'content_request_id': content_request.id
            })

    @staticmethod
    def push_verify_learning_result(progress_public_learning, is_queue):
        from .tasks_content_request import task_verify_learning_result
        if is_queue:
            task_verify_learning_result.delay(progress_public_learning.id)
        else:
            task_verify_learning_result(**{
                'progress_public_learning_id': progress_public_learning.id
            })

    @staticmethod
    def push_learning_result_status_completed_autocompleted(progress_public_learning, is_queue):
        from .tasks_content_request import task_learning_result_status_completed_autocompleted
        if is_queue:
            task_learning_result_status_completed_autocompleted.delay(progress_public_learning.id)
        else:
            task_learning_result_status_completed_autocompleted(**{
                'progress_public_learning_id': progress_public_learning.id
            })

    @staticmethod
    def push_learning_result_status_completed_autocompleted_user(progress_public_learning, is_queue):
        from .tasks_content_request import task_learning_result_status_completed_autocompleted_user
        if is_queue:
            task_learning_result_status_completed_autocompleted_user.delay(progress_public_learning.id)
        else:
            task_learning_result_status_completed_autocompleted_user(**{
                'progress_public_learning_id': progress_public_learning.id
            })

    @staticmethod
    def push_learning_result_status_failed_autocompleted(progress_public_learning, is_queue):
        from .tasks_content_request import task_learning_result_status_failed_autocompleted
        if is_queue:
            task_learning_result_status_failed_autocompleted.delay(progress_public_learning.id)
        else:
            task_learning_result_status_failed_autocompleted(**{
                'progress_public_learning_id': progress_public_learning.id
            })

    @staticmethod
    def push_learning_result_status_failed_autocompleted_user(progress_public_learning, is_queue):
        from .tasks_content_request import task_learning_result_status_failed_autocompleted_user
        if is_queue:
            task_learning_result_status_failed_autocompleted_user.delay(progress_public_learning.id)
        else:
            task_learning_result_status_failed_autocompleted_user(**{
                'progress_public_learning_id': progress_public_learning.id
            })

    @staticmethod
    def push_full_capacity_notification_dashboard(content, content_type, is_queue):
        from .tasks_push_full_capacity import task_push_full_capacity_notification_dashboard
        if is_queue:
            task_push_full_capacity_notification_dashboard.delay(content, content_type)
        else:
            task_push_full_capacity_notification_dashboard(**{
                'content': content,
                'content_type': content_type,
            })

    @staticmethod
    def push_discussion_notification_dashboard(comment, is_queue):
        from .tasks_push_discussion import task_push_discussion_notification_dashboard
        if is_queue:
            task_push_discussion_notification_dashboard.delay(comment.id)
        else:
            task_push_discussion_notification_dashboard(**{
                'comment_id': comment.id
            })

    @staticmethod
    def push_discussion_notification_user(comment, is_queue):
        from .tasks_push_discussion import task_push_discussion_notification_user
        if is_queue:
            task_push_discussion_notification_user.delay(comment.id)
        else:
            task_push_discussion_notification_user(**{
                'comment_id': comment.id
            })

    @staticmethod
    def push_update_learning_result(progress_public_learning, updated_account_id, is_queue):
        from .tasks_content_request import task_push_update_learning_result
        if is_queue:
            task_push_update_learning_result.delay(progress_public_learning.id,
                                                   updated_account_id)
        else:
            task_push_update_learning_result(**{
                'progress_public_learning_id': progress_public_learning.id,
                'updated_account_id': updated_account_id,
            })

    @staticmethod
    def push_new_content_permission(content_type_id, content_id, account_id, is_queue):
        from .tasks_push_content import task_push_new_content_permission
        if is_queue:
            task_push_new_content_permission.delay(content_type_id, content_id, account_id)
        else:
            task_push_new_content_permission(**{
                'content_type_id': content_type_id,
                'content_id': content_id,
                'account_id': account_id
            })

    @staticmethod
    def push_notify_approve_certificate(progress, is_queue):
        from .tasks_push_certificate import task_push_notify_approve_certificate
        code = f'{progress._meta.app_label}.{progress._meta.model_name}'
        progress_content_type = settings.CONTENT_TYPE(code)
        if is_queue:
            task_push_notify_approve_certificate.delay(progress_content_type.id, progress.id)
        else:
            task_push_notify_approve_certificate(**{
                'content_type_id': progress_content_type.id,
                'progress_id': progress.id
            })

    def push_result_learning_playlist_created(content_id, account_id_list, is_queue=False):
        from .tasks_learning_playlist import task_push_result_learning_playlist_created
        if is_queue:
            task_push_result_learning_playlist_created.delay(content_id, account_id_list)
        else:
            task_push_result_learning_playlist_created(**{
                'content_id': content_id,
                'account_id_list': account_id_list
            })

    @staticmethod
    def push_result_learning_playlist_assignment(assignment, is_queue=False):
        from .tasks_learning_playlist import task_push_result_learning_playlist_assignment
        if is_queue:
            task_push_result_learning_playlist_assignment.delay(assignment.id)
        else:
            task_push_result_learning_playlist_assignment(**{
                'assignment_id': assignment.id
            })

    @staticmethod
    def push_result_learning_playlist_content_added(playlist_id, is_queue=False):
        from .tasks_learning_playlist import task_push_result_learning_playlist_content_added
        if is_queue:
            task_push_result_learning_playlist_content_added.delay(playlist_id)
        else:
            task_push_result_learning_playlist_content_added(**{
                'playlist_id': playlist_id
            })

    @staticmethod
    def push_result_learning_playlist_approval(playlist_id, is_queue=False):
        from .tasks_learning_playlist import task_push_result_learning_playlist_approval
        if is_queue:
            task_push_result_learning_playlist_approval.delay(playlist_id)
        else:
            task_push_result_learning_playlist_approval(**{
                'playlist_id': playlist_id
            })

    @staticmethod
    def push_result_learning_playlist_recommended(playlist_id, is_queue=False):
        from .tasks_learning_playlist import task_push_result_learning_playlist_recommended
        if is_queue:
            task_push_result_learning_playlist_recommended.delay(playlist_id)
        else:
            task_push_result_learning_playlist_recommended(**{
                'playlist_id': playlist_id
            })

    @staticmethod
    def push_content_cancel(transaction, account_list, is_queue, is_dashboard=False, is_approve=False, account_full_name=''):
        from .tasks_content_cancel import task_push_cancel
        if is_queue:
            task_push_cancel.delay(transaction_id=transaction.id,
                                   account_list=account_list,
                                   is_dashboard=is_dashboard,
                                   is_approve=is_approve,
                                   account_full_name=account_full_name)
        else:
            task_push_cancel.apply(**{
                'transaction_id': transaction.id,
                'account_list': account_list,
                'is_dashboard': is_dashboard,
                'is_approve': is_approve,
                'account_full_name': account_full_name
            })

    @staticmethod
    def push_identification_revision_account_verify(revision_id, revision_account_id, is_queue):
        from .tasks_identification_verify import task_push_identification_revision_account_verify
        if is_queue:
            task_push_identification_revision_account_verify.delay(revision_id=revision_id,
                                                                   revision_account_id=revision_account_id)
        else:
            task_push_identification_revision_account_verify.apply(**{
                'revision_id': revision_id,
                'revision_account_id': revision_account_id
            })

    @staticmethod
    def push_identification_revision_account_verify_user(revision_account_id, is_queue):
        from .tasks_identification_verify import task_push_identification_revision_account_verify_user
        if is_queue:
            task_push_identification_revision_account_verify_user.delay(revision_account_id=revision_account_id)
        else:
            task_push_identification_revision_account_verify_user.apply(**{
                'revision_account_id': revision_account_id
            })

    def send_notification(self):
        from config.models import Config

        if not settings.TESTING:
            device_list = Config.pull_value('notification-device-list')
            if settings.IS_SEND_EMAIL and 'mail' in device_list:
                self.send_notification_email()
            if settings.IS_SEND_FCM and 'fcm' in device_list:
                self.send_notification_fcm()

            self.status = 1
            self.datetime_send = timezone.now()
            self.save(update_fields=['status', 'datetime_send'])
            self.update_count_flag()

    def send_notification_email(self):
        from mailer.models import Mailer
        from account.models import Account
        from utils.content import get_content
        from .mail import get_body, get_subject
        if not Config.pull_value('config-mailer-is-enable') or settings.IS_LOCALHOST:
            return

        for account_id in self.member_set.values_list('account_id', flat=True):
            account = Account.pull(account_id)


            if not account.email or not account.is_subscribe:
                continue

            # if not (Rule.check_is_consent(account_id, 'data_consent_user_information')):
            #     continue

            email = account.email
            body = get_body(self, account)
            subject = get_subject(self)
            attach_file = None
            mailer = Mailer.objects.create(
                subject=subject,
                body=body,
                to=email,
                type=2,
                attach_file=attach_file,
                inbox=self
            )

            # Transaction For Event Success
            if self.type == 11:
                transaction = Transaction.pull(self.content_id)
                content = get_content(transaction.content_type_id, transaction.content_id)
                if content is not None:
                    if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
                        if content.is_session_enrollment_config_enabled:
                            progress_event = ProgressEvent.pull(transaction.account_id, transaction.content_id)
                            session_enroll_id_list = SessionEnrollment.pull_list_by_progress(progress_event.id).values_list('session_id',
                                                                                                          flat=True).exclude(
                                session__type=0)
                            session_list = Session.objects.filter(id__in=session_enroll_id_list)
                            if session_enroll_id_list.exists():
                                session_first = session_list.first()
                                session_last = session_list.last()
                                calendar = create_ics_file('Event Calendar', content.name, session_first.datetime_start,
                                                           session_last.datetime_end)
                                mailer.attach_file.save('invite.ics', ContentFile(calendar.to_ical()))
                        else:
                            calendar = create_ics_file('Event Calendar', content.name, content.datetime_start,
                                                       content.datetime_end)
                            mailer.attach_file.save('invite.ics', ContentFile(calendar.to_ical()))

            if body is None:
                return

            mailer.send()

    def send_notification_fcm(self):
        from utils.content import get_code
        if settings.IS_LOCALHOST:
            return
        setting = self.config_fcm['settings']
        api_key_list = setting['FCM_SERVER_KEY']

        api_key = api_key_list[0]

        for account_id in self.member_set.values_list('account_id', flat=True):
            # if not (Rule.check_is_consent(account_id, 'data_consent_user_information')):
            #     continue
                
            if self.type in [1, 2, 30, 31, 32, 210]:
                data = self.get_body_fcm_data()
                try:
                    self._send_fcm(account_id=account_id,
                                   title=self.title,
                                   body=self.body,
                                   click_action=self.click_action,
                                   data=data,
                                   server_key=api_key,
                                   code=get_code(self.content_type))
                except Exception as error:
                    print('Fcm error %s' % error)
            else:
                for content in self.content_set.all():
                    try:
                        self._send_fcm(account_id=account_id,
                                       title=self.title,
                                       body=content.get_body(),
                                       click_action=self.click_action,
                                       data=content.get_fcm_data(),
                                       server_key=api_key,
                                       code=get_code(content.content_type))
                    except Exception as error:
                        print('Fcm error %s' % error)

    def _send_fcm(self, account_id, title, body, data, click_action, server_key, code, **kwargs):
        from fcm_django.models import FCMDevice
        from fcm_django.fcm import fcm_send_message
        from transaction.models import Transaction
        account_register_list = FCMDevice.objects.filter(user_id=account_id, active=True)
        if account_register_list.exists():
            for account_register in account_register_list:
                if self.type in [30, 31, 32]:
                    transaction = Transaction.objects.filter(account_id=account_id,
                                                             content_type=self.content_type,
                                                             content_id=self.content_id,
                                                             status=0).first()
                    if transaction:
                        title = "%s %s" % (title, transaction.get_method_display())
                if account_register.type == u'android':
                    badge = Inbox.objects.filter(read__isnull=True, member__account_id=account_id).count()
                    sound = 'default'
                    # data.update({
                    #     'title': title,
                    #     'body': body
                    # })
                    # title = None
                    # body = None
                    # click_action = None
                elif account_register.type == u'ios':
                    sound = 'default'
                    badge = Inbox.objects.filter(status=1, member__account_id=account_id, read__isnull=True).count()
                else:
                    continue

                result = fcm_send_message(registration_id=account_register.registration_id,
                                          title=title,
                                          body=body,
                                          data=data,
                                          badge=badge,
                                          sound=sound,
                                          click_action=click_action,
                                          api_key=server_key,
                                          **kwargs)
                if result['success'] == 0:
                    account_register.active = False
                    account_register.save(update_fields=['active'])

    def get_body_fcm_data(self):
        from inbox.serializer_fcm import FCMInboxSerializer
        if self.type in [1, 2, 30, 210]:
            return FCMInboxSerializer(instance=self).data

    def update_count_flag(self):
        from .caches import cache_account_count_delete
        account_id_list = self.member_set.all().values_list('account_id', flat=True)
        Count.objects.filter(account_id__in=account_id_list, is_dashboard=self.is_dashboard).update(count=1)
        for account_id in account_id_list:
            cache_account_count_delete(account_id)

    @staticmethod
    def get_email_detail_list(event_list, account, enroll_status=None):
        from check_in.models import Content as CheckinContent
        from progress_event.models import SessionEnrollment, ProgressEvent

        _event_list = []
        item_list = []

        content_type = None
        is_session_enrollment = False

        for event in event_list:
            index = 0
            qr_code_holder = event.qr_code_holder
            check_in_group = event.check_in_group

            _event = {
                'id': event.id,
                'name': event.name,
                'check_in_group': check_in_group,
                'qr_code_holder': qr_code_holder,
                'qr_list': []
            }

            session_enroll_id_list = []
            if event.is_session_enrollment_config_enabled:
                transaction = Transaction.pull_by_content(
                    account=account,
                    content_type=settings.CONTENT_TYPE('event.event'),
                    content_id=event.id,
                )

                progress_event = ProgressEvent.pull(transaction.account_id, transaction.content_id)
                session_enroll_list = SessionEnrollment.pull_list_by_progress(progress_event.id).select_related('session')
                session_enroll_id_list = session_enroll_list.values_list('session_id', flat=True)
                is_session_enrollment = session_enroll_list.exists()

                # Enroll success, not reserve session
                if not is_session_enrollment:
                    if check_in_group == 0:
                        item_list = event.session_set.filter(type__in=[2, 3])
                        content_type = settings.CONTENT_TYPE('event.session')
                    elif check_in_group in [1, 2]:
                        content_type = settings.CONTENT_TYPE('event.schedule')
                        item_list = EventSchedule.objects.filter(event_id=event.id)
                else:  # Enroll success, reserved session success
                    if check_in_group == 0:
                        item_list = event.session_set.filter(id__in=session_enroll_id_list)
                        content_type = settings.CONTENT_TYPE('event.session')
                    elif check_in_group in [1, 2]:
                        content_type = settings.CONTENT_TYPE('event.schedule')
                        item_list = EventSchedule.objects.filter(event_id=event.id)

                _is_qr_code = True if enroll_status == 0 and qr_code_holder == 0 else False
                _event.update({
                    'is_qr_code': _is_qr_code,
                    'is_session_enrollment': is_session_enrollment
                })

            else:
                if check_in_group == 0:
                    item_list = event.session_set.filter(type__in=[2, 3])
                    content_type = settings.CONTENT_TYPE('event.session')
                elif check_in_group in [1, 2]:
                    content_type = settings.CONTENT_TYPE('event.schedule')
                    item_list = EventSchedule.objects.filter(event_id=event.id)

                _is_qr_code = True if enroll_status == 0 and qr_code_holder == 0 else False
                _event.update({
                    'is_qr_code': _is_qr_code,
                    'is_session_enrollment': is_session_enrollment
                })

            # qr code by class
            if check_in_group == 2:
                for item in item_list:
                    session_list = []
                    if event.is_session_enrollment_config_enabled and is_session_enrollment:
                        for session in item.session_set.filter(type__in=[2, 3], id__in=session_enroll_id_list):
                            session_list.append(session)
                    else:
                        for session in item.session_set.filter(type__in=[2, 3]):
                            session_list.append(session)

                    if session_list:
                        if qr_code_holder == 0:
                            qr_code = ProgressCheckIn.pull(
                                settings.CONTENT_TYPE('event.event'),
                                event.id,
                                account.id
                            )
                        else:
                            qr_code = None

                        _qr = {
                            'code': qr_code.code if qr_code else None,
                            'image': qr_code.qr_code.url if qr_code else None,
                            'session_list': []
                        }

                        for session in session_list:
                            index += 1
                            _qr['session_list'].append({
                                'index': index,
                                'name': session.name,
                                'date': convert_to_local(session.datetime_start).date().strftime('%d %b %Y'),
                                'start_time': convert_to_local(session.datetime_start).time(),
                                'end_time': convert_to_local(session.datetime_end).time(),
                                'location': session.location,
                            })
                        _event['qr_list'].append(_qr)

            # qr code by session or days
            else:
                for item in item_list:
                    session_list = []
                    if isinstance(item, EventSession):
                        session_list.append(item)
                    elif isinstance(item, EventSchedule):
                        if event.is_session_enrollment_config_enabled and session_enroll_id_list.exists():
                            for session in item.session_set.filter(type__in=[2, 3], id__in=session_enroll_id_list):
                                session_list.append(session)
                        else:
                            for session in item.session_set.filter(type__in=[2, 3]):
                                session_list.append(session)
                    checkin_content = CheckinContent.pull(content_type, item.id)

                    if checkin_content and session_list:
                        if qr_code_holder == 0:
                            qr_code = ProgressCheckIn.pull(
                                settings.CONTENT_TYPE('check_in.checkin'),
                                checkin_content.check_in_id,
                                account.id
                            )
                        else:
                            qr_code = None

                        _qr = {
                            'code': qr_code.code if qr_code else None,
                            'image': qr_code.qr_code.url if qr_code else None,
                            'session_list': []
                        }

                        for session in session_list:
                            index += 1
                            _qr['session_list'].append({
                                'index': index,
                                'name': session.name,
                                'date': convert_to_local(session.datetime_start).date().strftime('%d %b %Y'),
                                'start_time': convert_to_local(session.datetime_start).time(),
                                'end_time': convert_to_local(session.datetime_end).time(),
                                'location': session.location,
                            })
                        _event['qr_list'].append(_qr)
            if _event:
                _event_list.append(_event)
        return _event_list


class Content(models.Model):
    inbox = models.ForeignKey(Inbox, on_delete=models.CASCADE)
    content_type = models.ForeignKey('contenttypes.ContentType', related_name='+', on_delete=models.CASCADE)
    content_id = models.PositiveIntegerField()
    content = GenericForeignKey('content_type', 'content_id')

    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()
        ordering = ['id']

    def __str__(self):
        return "%s" % self.content_type.app_label

    @property
    def click_action(self):
        if self.content_type == settings.CONTENT_TYPE('event.event'):
            page = 'CLASS'
        else:
            page = self.content_type.app_label.upper()

        return 'OPEN_%s_DETAIL' % page

    def provider(self):
        from provider.models import Provider
        return Provider.objects.filter(content__content_id=self.content_id,
                                       content__content_type_id=self.content_type.id).first()

    def get_body(self):
        return getattr(self.content, 'name', self.content_type.app_label)

    def get_fcm_data(self):
        if self.inbox.type in [10, 11, 12, 20, 21, 22, 23, 30, 31, 40, 41, 50, 51]:
            from inbox.serializer_fcm import FCMContenSerializer
            return FCMContenSerializer(instance=self).data

    def get_site_url(self):
        from config.models import Config
        site_url = Config.pull_value('config-site-url')
        if settings.CONTENT_TYPE('event.event').id == self.content_type_id:
            path = 'class'
        elif settings.CONTENT_TYPE('exam.exam').id == self.content_type_id:
            path = 'test'
        elif settings.CONTENT_TYPE('learning_path.learningpath').id == self.content_type_id:
            path = 'learning-path'
        else:
            path = self.content_type.app_label
        return '%s/%s/%s' % (site_url, path, self.content_id)


class Member(models.Model):
    inbox = models.ForeignKey(Inbox, on_delete=models.CASCADE)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name='+', on_delete=models.CASCADE)
    sort = models.IntegerField(default=0, db_index=True)
    is_dashboard = models.BooleanField(default=False, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()
        ordering = ['id']

    def __str__(self):
        return '%s' % self.account.email


class Count(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)
    is_dashboard = models.BooleanField(default=False, db_index=True)
    is_updated = models.BooleanField(default=False, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    datetime_update = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()

    @staticmethod
    def pull(account):
        from .caches import cache_account_count
        return cache_account_count(account)

    def add(self):
        from .caches import cache_account_count_delete, cache_dashboard_account_count_delete
        self.count += 1
        self.save(update_fields=['count'])
        if self.is_dashboard:
            cache_dashboard_account_count_delete(self.account)
        else:
            cache_account_count_delete(self.account.id)

    def clear_count(self):
        from .caches import cache_account_count_delete, cache_dashboard_account_count_delete
        self.count = 0
        self.save(update_fields=['count'])
        if self.is_dashboard:
            cache_dashboard_account_count_delete(self.account)
        else:
            cache_account_count_delete(self.account.id)


class Read(models.Model):
    inbox = models.ForeignKey(Inbox, on_delete=models.CASCADE)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_dashboard = models.BooleanField(default=False, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True)
    datetime_update = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()

    @staticmethod
    def is_read(inbox, account):
        return Read.objects.filter(
            inbox=inbox,
            account=account
        ).exists()

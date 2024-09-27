from celery import shared_task
from django.conf import settings

from inbox.models import Inbox
from progress_exam.models import ProgressExam


@shared_task(bind=True, queue='user')
def task_push_progress_exam_announcement(self, progress_exam_id):
    title = 'exam_announcement_job title'
    body = 'exam_announcement_job body'
    detail = 'exam_announcement_job detail'
    sender = None

    progress_exam = ProgressExam.objects.filter(id=progress_exam_id).first()
    if progress_exam is None:
        return None

    transaction = progress_exam.transaction
    inbox = Inbox.push(
        sender=sender,
        inbox_type=61,
        inbox_content_type=settings.CONTENT_TYPE('transaction.transaction'),
        inbox_content_id=transaction.id,
        content_id=transaction.content_id,
        content_type=transaction.content_type,
        account=transaction.account,
        title=title,
        body=body,
        detail=detail
    )
    inbox.send_notification()


@shared_task(bind=True, queue='user')
def task_push_progress_exam_answer_key(self, progress_exam_id):
    title = 'exam_answer_key_job title'
    body = 'exam_answer_key_job body'
    detail = 'exam_answer_key_job detail'
    sender = None

    progress_exam = ProgressExam.objects.filter(id=progress_exam_id).first()
    if progress_exam is None:
        return None

    transaction = progress_exam.transaction
    inbox = Inbox.push(
        sender=sender,
        inbox_type=62,
        inbox_content_type=settings.CONTENT_TYPE('transaction.transaction'),
        inbox_content_id=transaction.id,
        content_id=transaction.content_id,
        content_type=transaction.content_type,
        account=transaction.account,
        title=title,
        body=body,
        detail=detail
    )
    inbox.send_notification()

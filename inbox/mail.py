from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from account.models import Account
from account.models import IdentityVerification
from activity.models import Activity
from config.models import Config
from content_request.models import ContentRequest
from course.models import Course
from event.models import Event
from exam.models import Exam
from inbox.models import Inbox
from learning_path.models import LearningPath
from news_update.models import NewsUpdate
from onboard.models import Onboard
from progress_content_request.models import ProgressContentRequest, ProgressStep
from provider.models import Content as ProviderContent
from provider.models import Provider
from public_learning.models import PublicLearning
from survey.models import Survey
from transaction.models import Transaction
from utils.content import get_content, get_content_url
from utils.content_type import get_content_type_name


def get_body(inbox, account):
    site_url = Config.pull_value('config-site-url')
    header_image = Config.pull_value('mailer-header-image')
    event_list = []
    query_str = ''

    if inbox.type == 1:  # Direct Message
        return render_to_string(
            'mailer/inbox/direct_message.html',
            {
                'header_image': header_image,
                'title': inbox.title,
                'body': inbox.body,
            }
        )
    elif inbox.type == 2:  # News Update
        news_update = NewsUpdate.pull(inbox.content_id)
        if news_update is None:
            return None

        site = '%s/news/%s' % (Config.pull_value('config-site-url'), news_update.id)
        app_name = Config.pull_value('config-app-name')
        return render_to_string(
            'mailer/inbox/news_update.html',
            {
                'header_image': header_image,
                'app_name': app_name,
                'title': inbox.title,
                'body': inbox.body,
                'site': site,
                'news': news_update,
            }
        )
    elif inbox.type == 10:  # Assignment
        email_footer = 0
        _content_list = []
        is_event_within_content_list = False
        for content in inbox.content_set.all():
            if content.content_type_id == settings.CONTENT_TYPE('event.event').id:
                event = Event.pull(content.content_id)
                event_program_id = event.event_program_id if event.event_program else -1
                provider_content = ProviderContent.objects.filter(
                    content_id=event_program_id,
                    content_type_id=settings.CONTENT_TYPE('event_program.eventprogram').id
                ).first()
                is_event_within_content_list = True
            else:
                provider_content = ProviderContent.objects.filter(
                    content_id=content.content_id,
                    content_type_id=content.content_type_id
                ).first()

            if provider_content is None:
                provider_name = '-'
            else:
                provider_name = provider_content.provider.name

            if content.content_type_id == settings.CONTENT_TYPE('event.event').id:
                event = Event.pull(content.content_id)
                site = '%s/class/%s/' % (site_url, event.id)
                type = 'Class'
                email_footer = 1
                event_list.append(event)

                event_program_name = event.event_program.name if event.event_program else ''
                content_name = '%s (%s)' % (event_program_name, event.name)
                setattr(content, 'name', content_name)

            elif content.content_type_id == settings.CONTENT_TYPE('course.course').id:
                content = Course.objects.filter(id=content.content_id).first()
                site = '%s/course/%s/' % (site_url, content.id)
                type = 'Course'

            elif content.content_type_id == settings.CONTENT_TYPE('onboard.onboard').id:
                content = Onboard.objects.filter(id=content.content_id).first()
                site = '%s/onboard/%s/' % (site_url, content.id)
                type = 'Onboard'

            elif content.content_type_id == settings.CONTENT_TYPE('survey.survey').id:
                content = Survey.objects.filter(id=content.content_id).first()
                site = '%s/survey/%s/' % (site_url, content.id)
                type = 'Survey'

            elif content.content_type_id == settings.CONTENT_TYPE('exam.exam').id:
                content = Exam.objects.filter(id=content.content_id).first()
                site = '%s/test/%s/' % (site_url, content.id)
                type = 'Test'

            elif content.content_type_id == settings.CONTENT_TYPE('activity.activity').id:
                content = Activity.objects.filter(id=content.content_id).first()
                site = '%s/activity/%s/' % (site_url, content.id)
                type = 'Activity'

            elif content.content_type_id == settings.CONTENT_TYPE('learning_path.learningpath').id:
                content = LearningPath.objects.filter(id=content.content_id).first()
                if content.type_learning_path == 0:
                    site = '%s/learning-path/%s/' % (site_url, content.id)
                    type = 'Learning path'
                else:
                    site = '%s/learning-path/%s/curriculum?is_schedule=true' % (site_url, content.id)
                    type = 'Learning path'

            elif content.content_type_id == settings.CONTENT_TYPE('public_learning.publiclearning').id:
                content = PublicLearning.objects.filter(id=content.content_id).first()
                site = '%s/public-learning/%s/' % (site_url, content.id)
                type = 'Public learning'
            else:
                content = -1
                site = 'Unknown'
                type = 'Unknown'

            data = {
                'provider': provider_name,
                'content': content,
                'site': site,
                'type': type,
            }
            _content_list.append(data)

        is_session_enrollment = False
        if event_list:
            event_list = Inbox.get_email_detail_list(event_list, account)
            is_session_enrollment = True if len(event_list) > 1 else event_list[0].get('is_session_enrollment', -1)
        name = account.first_name + ' ' + account.last_name
        text = 'You received new assignment (คุณ %s ได้รับการมอบหมายใหม่ )' % name

        return render_to_string(
            'mailer/inbox/assignment.html',
            {
                'header_image': header_image,
                'site': site,
                'text': text,
                'content_list': _content_list,
                'event_list': event_list,
                'email_footer': email_footer,
                'inbox': inbox,
                'is_session_info': Config.pull_value('qr-code-email') and is_event_within_content_list,
                'main_color': Config.pull_value('content-email-main-color'),
                'background_color': Config.pull_value('content-email-background-color'),
                'is_session_enrollment': is_session_enrollment,
            }
        )
    elif inbox.type == 11:  # Transaction_Success
        template = 'mailer/inbox/enrolled_and_reminder.html'
        transaction = Transaction.pull(inbox.content_id)
        content = get_content(transaction.content_type_id, transaction.content_id)
        name = account.first_name + ' ' + account.last_name
        event_context = None
        email_footer = 0

        if transaction is None:
            return None
        if settings.CONTENT_TYPE('event.event').id is transaction.content_type_id:
            path = 'class'
            is_session_info = Config.pull_value('qr-code-email')
            event_id = Transaction.objects.filter(id=inbox.content_id).first().content_id
            event = Event.objects.filter(id=event_id)
            event_list = Inbox.get_email_detail_list(event, account, 0)

            event_program_name = content.event_program.name if content.event_program else ''
            content_name = '%s (%s)' % (event_program_name, content.name)
            setattr(content, 'name', content_name)

            email_footer = 1
            is_session_enrollment = event_list[0]['is_session_enrollment'] if event_list else False
            show_qr_code = event_list[0]['is_qr_code'] if event_list else False
            qr_code_holder = event_list[0]['qr_code_holder'] if event_list else -1
            event_context = {
                'is_session_info': is_session_info,
                'is_session_enrollment': is_session_enrollment,
                'show_qr_code': show_qr_code,
                'qr_code_holder': qr_code_holder,
            }

        elif settings.CONTENT_TYPE('exam.exam').id is transaction.content_type_id:
            path = 'test'
        elif settings.CONTENT_TYPE('course.course').id is transaction.content_type_id:
            path = 'course'
        elif settings.CONTENT_TYPE('learning_path.learningpath').id is transaction.content_type_id:
            learning_path = LearningPath.pull(transaction.content_id)
            path = 'learning-path'
            if learning_path.type_learning_path == 1:
                query_str = 'curriculum?is_schedule=true'
        else:
            path = transaction.content_type.app_label

        site = '%s/%s/%s/%s' % (site_url, path, transaction.content_id, query_str)
        provider = Provider.objects.filter(
            content__content_id=transaction.content_id,
            content__content_type_id=transaction.content_type_id
        ).first()

        basedir = settings.BASE_DIR
        text = 'Congratulations!, You have successfully enrolled (ยินดีด้วย! คุณ %s ได้ทำการลงทะเบียนสำเร็จ)' % name

        return render_to_string(
            'mailer/inbox/enrolled_and_reminder.html',
            {
                'header_image': header_image,
                'text': text,
                'inbox': inbox,
                'site': site,
                'event_list': event_list,
                'content': get_content(transaction.content_type_id, transaction.content_id),
                'email_footer': email_footer,
                'provider': provider,
                'basedir': basedir,
                'main_color': Config.pull_value('content-email-main-color'),
                'background_color': Config.pull_value('content-email-background-color'),
                'content_name': content.name,
                'event_context': event_context
            }
        )

    elif inbox.type == 12:  # Transaction Reject
        transaction = Transaction.pull(inbox.content_id)
        if transaction is None:
            return None
        content = get_content(transaction.content_type_id, transaction.content_id)
        return render_to_string(
            'mailer/inbox/transaction_reject.html',
            {
                'header_image': header_image,
                'content': content,
            }
        )
    elif inbox.type == 20:  # Progress Completed
        transaction = Transaction.pull(inbox.content_id)
        if transaction is None:
            return None

        if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        elif settings.CONTENT_TYPE('exam.exam').id is transaction.content_type_id:
            path = 'test'
        elif settings.CONTENT_TYPE('learning_path.learningpath').id is transaction.content_type_id:
            learning_path = LearningPath.pull(transaction.content_id)
            path = 'learning-path'
            if learning_path.type_learning_path == 1:
                query_str = 'curriculum?is_schedule=true'
        else:
            path = settings.CONTENT_TYPE_ID(transaction.content_type.id).app_label
        site = '%s/%s/%s/%s' % (site_url, path, transaction.content_id, query_str)
        provider = Provider.objects.filter(content__content_id=transaction.content_id,
                                           content__content_type_id=transaction.content_type_id).first()
        return render_to_string(
            'mailer/inbox/progress_completed.html',
            {
                'header_image': header_image,
                'inbox': inbox,
                'site': site,
                'content': get_content(transaction.content_type_id, transaction.content_id),
                'provider': provider,
            }
        )
    elif inbox.type == 21:  # Progress Fail
        transaction = Transaction.pull(inbox.content_id)
        if transaction is None:
            return None

        if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        elif settings.CONTENT_TYPE('exam.exam').id is transaction.content_type_id:
            path = 'test'
        elif settings.CONTENT_TYPE('learning_path.learningpath').id is transaction.content_type_id:
            learning_path = LearningPath.pull(transaction.content_id)
            path = 'learning-path'
            if learning_path.type_learning_path == 1:
                query_str = 'curriculum?is_schedule=true'
        else:
            path = transaction.content_type.app_label

        site = '%s/%s/%s/%s' % (site_url, path, transaction.content_id, query_str)
        provider = Provider.objects.filter(content__content_type_id=transaction.content_type_id,
                                           content__content_id=transaction.content_id).first()
        return render_to_string(
            'mailer/inbox/progress_fail.html',
            {
                'header_image': header_image,
                'inbox': inbox,
                'site': site,
                'content': get_content(transaction.content_type_id, transaction.content_id),
                'provider': provider,
            }
        )
    elif inbox.type == 22:  # Progress Verifying
        transaction = Transaction.pull(inbox.content_id)
        if transaction is None:
            return None

        if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        elif settings.CONTENT_TYPE('exam.exam').id is transaction.content_type_id:
            path = 'test'
        elif settings.CONTENT_TYPE('learning_path.learningpath').id is transaction.content_type_id:
            learning_path = LearningPath.pull(transaction.content_id)
            path = 'learning-path'
            if learning_path.type_learning_path == 1:
                query_str = 'curriculum?is_schedule=true'
        else:
            path = transaction.content_type.app_label
        site = '%s/%s/%s/%s' % (site_url, path, transaction.content_id, query_str)
        return render_to_string(
            'mailer/inbox/progress_verifying.html',
            {
                'header_image': header_image,
                'inbox': inbox,
                'content': get_content(transaction.content_type_id, transaction.content_id),
                'site': site,
                'content_typ_name_event': settings.CONTENT_TYPE('event.event'),
            }
        )
    elif inbox.type == 23:  # Progress Expired
        transaction = Transaction.pull(inbox.content_id)
        if transaction is None:
            return None

        content = get_content(transaction.content_type_id, transaction.content_id)
        datetime_expired = timezone.localtime().strftime('%A %d %B %Y %H:%M %p')
        if content and hasattr(content, 'datetime_end') and content.datetime_end:
            datetime_expired = timezone.localtime(content.datetime_end).strftime('%A %d %B %Y %H:%M %p')

        if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
            site = '%s/class/%s/' % (site_url, transaction.content_id)
        elif transaction.content_type_id == settings.CONTENT_TYPE('exam.exam').id:
            site = '%s/test/%s/' % (site_url, transaction.content_id)
        elif settings.CONTENT_TYPE('learning_path.learningpath').id is transaction.content_type_id:
            learning_path = LearningPath.pull(transaction.content_id)
            if learning_path.type_learning_path == 0:
                site = '%s/learning-path/%s/' % (site_url, transaction.content_id)
            else:
                site = '%s/learning-path/%s/curriculum?is_schedule=true' % (site_url, transaction.content_id)
        else:
            path = transaction.content_type.app_label
            site = '%s/%s/%s/' % (site_url, path, transaction.content_id)

        return render_to_string(
            'mailer/inbox/progress_expired.html',
            {
                'header_image': header_image,
                'inbox': inbox,
                'content': content,
                'site': site,
                'datetime_expired': datetime_expired,
            }
        )
    elif inbox.type in [30, 31]:  # 30-Content Start, 31-Before Content start

        transaction = Transaction.objects.filter(
            content_type=inbox.content_type,
            content_id=inbox.content_id,
            account=account,
            status=0
        ).first()
        if not transaction:
            return None
        event = Event.objects.filter(id=inbox.content_id)
        event_list = Inbox.get_email_detail_list_old(event, account)
        content = get_content(inbox.content_type_id, inbox.content_id)
        if content is None:
            content_name = inbox.content_type.app_label
            time_start = timezone.datetime.now().strftime('%d %B %y %H:%M %p')
        else:
            content_name = getattr(content, 'name', inbox.content_type.app_label)
            datetime_start = getattr(content, 'datetime_start', None)
            if datetime_start:
                time_start = timezone.localtime(datetime_start).strftime('%d %B %y %H:%M %p')
            else:
                time_start = timezone.datetime.now().strftime('%d %B %y %H:%M %p')

        title = 'Hi, Your %s' % transaction.get_method_display()
        body = 'will start on %s' % time_start

        if settings.CONTENT_TYPE('event.event').id == inbox.content_type_id:
            site = '%s/class/%s/' % (site_url, inbox.content_id)
        elif settings.CONTENT_TYPE('exam.exam').id == inbox.content_type_id:
            site = '%s/test/%s/' % (site_url, inbox.content_id)
        elif settings.CONTENT_TYPE('learning_path.learningpath').id == inbox.content_type_id:
            learning_path = LearningPath.pull(inbox.content_id)
            if learning_path.type_learning_path == 0:
                site = '%s/learning-path/%s/' % (site_url, inbox.content_id)
            else:
                site = '%s/learning-path/%s/curriculum?is_schedule=true' % (site_url, inbox.content_id)
        else:
            site = '%s/%s/%s/' % (site_url, inbox.content_type.app_label, inbox.content_id)
        name = account.first_name + ' ' + account.last_name
        text = 'Reminder(แจ้งเตือน คุณ %s)' % name
        return render_to_string(
            'mailer/inbox/enrolled_and_reminder.html',
            {
                'header_image': header_image,
                'text': text,
                'title': title,
                'body': body,
                'event_list': event_list,
                'content_name': content_name,
                'site': site,
                'main_color': Config.pull_value('content-email-main-color'),
                'email_footer': 1,
                'config': True,
                'background_color': Config.pull_value('content-email-background-color')
            }
        )

    elif inbox.type == 32:  # Content Cancelled
        content = get_content(inbox.content_type_id, inbox.content_id)
        if settings.CONTENT_TYPE('event.event').id == inbox.content_type_id:
            site = '%s/class/%s/' % (site_url, inbox.content_id)
        elif settings.CONTENT_TYPE('exam.exam').id == inbox.content_type_id:
            site = '%s/test/%s/' % (site_url, inbox.content_id)
        elif settings.CONTENT_TYPE('learning_path.learningpath').id == inbox.content_type_id:
            learning_path = LearningPath.pull(inbox.content_id)
            if learning_path.type_learning_path == 0:
                site = '%s/learning-path/%s/' % (site_url, inbox.content_id)
            else:
                site = '%s/learning-path/%s/curriculum?is_schedule=true' % (site_url, inbox.content_id)
        else:
            site = '%s/%s/%s' % (site_url, inbox.content_type.app_label, inbox.content_id)

        return render_to_string(
            'mailer/inbox/content_cancel.html',
            {
                'header_image': header_image,
                'inbox': inbox,
                'site': site,
                'content_name': content.name,
            }
        )
    elif inbox.type == 40:  # Approved Certificate
        transaction = Transaction.pull(inbox.content_id)
        content = get_content(transaction.content_type_id, transaction.content_id)
        if transaction.content_type_id == settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        elif transaction.content_type_id == settings.CONTENT_TYPE('exam.exam').id:
            path = 'test'
        else:
            path = transaction.content_type.app_label

        site = '%s/%s/%s/' % (site_url, path, content.id)


        return render_to_string(
            'mailer/inbox/certificate_approve.html',
            {
                'header_image': header_image,
                'site': site,
                'content_name': getattr(content, 'name', None)
            }
        )
    elif inbox.type == 41:  # UnApproved Certificate
        transaction = Transaction.pull(inbox.content_id)
        content = get_content(transaction.content_type_id, transaction.content_id)
        if transaction.content_type_id is settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        else:
            path = transaction.content_type.app_label

        site = '%s/%s/%s/' % (site_url, path, content.id)


        return render_to_string(
            'mailer/inbox/certificate_unapprove.html',
            {
                'header_image': header_image,
                'site': site,
                'content_name': getattr(content, 'name', None)
            }
        )
    elif inbox.type == 50:  # Check in Complete
        inbox_content = inbox.content_set.all().first()
        if inbox_content.content_type_id is settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        else:
            path = inbox_content.content_type.app_label

        site = '%s/%s/%s/' % (site_url, path, inbox_content.content_id)
        content = get_content(inbox_content.content_type_id, inbox_content.content_id)

        return render_to_string(
            'mailer/inbox/check_in_complete.html',
            {
                'header_image': header_image,
                'site': site,
                'content_name': getattr(content, 'name', None)
            }
        )

    elif inbox.type == 51:  # Check in Fail
        inbox_content = inbox.content_set.all().first()

        if inbox_content.content_type_id is settings.CONTENT_TYPE('event.event').id:
            path = 'class'
        else:
            path = inbox_content.content_type.app_label

        site = '%s/%s/%s/' % (site_url, path, inbox.content_id)
        content = get_content(inbox_content.content_type_id, inbox_content.content_id)

        return render_to_string(
            'mailer/inbox/check_in_failed.html',
            {
                'header_image': header_image,
                'site': site,
                'content_name': getattr(content, 'name', None)
            }
        )
    elif inbox.type in [60, 61, 62]:  # Progress Exam
        type_label = {
            60: 'Progress Exam Start',
            61: 'Progress Exam Announcement',
            62: 'Progress Exam Answer Key'
        }
        return '<p> %s </p>' % type_label[inbox.type]
    elif inbox.type in [70, 73]:  # Content Request
        content_request = ContentRequest.pull(inbox.content_id)
        progress_content_request = ProgressContentRequest.pull(content_request)
        content = get_content(content_request.content_type_id, content_request.content_id)
        date_str_list = content_request.get_start_to_end_date
        account_list = content_request.content_request_account.all()
        progress_step = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                    status=1).order_by('step__step').last()
        link_detail = 1
        expire_detail = 1
        title = 'You are in Learner List of the Public Request.'
        if inbox.type == 73:
            link_detail = 0
            title = 'Your team member are in learner list of the public request.'
        content_type = get_content_type_name(content.content_type['id'])

        if content_request.content_type_id == settings.CONTENT_TYPE('event.event').id:
            event_program_name = content.event_program.name if content.event_program else ''
            content_name = '%s (%s)' % (event_program_name, content.name)
            setattr(content, 'name', content_name)

        if settings.CONTENT_TYPE('public_learning.publiclearning').id == content_request.content_type_id:
            site = get_content_url(settings.CONTENT_TYPE('content_request.contentrequest').id, content_request.id)
        else:
            site = get_content_url(content_request.content_type_id, content_request.content_id)
            if progress_step and not progress_step.datetime_end or not progress_step:
                expire_detail = 0
        price = "{:,.2f}".format(content_request.price)
        return render_to_string(
            'mailer/inbox/content_request.html',
            {
                'header_image': header_image,
                'content_request': content_request,
                'progress_content_request': progress_content_request,
                'progress_step': progress_step,
                'account_list': account_list,
                'date_list': date_str_list,
                'content': content,
                'content_type': content_type,
                'link_detail': link_detail,
                'expire_detail': expire_detail,
                'price': price,
                'title': title,
                'site': site
            }
        )
    elif inbox.type in [71]:  # Content Request
        content_request = ContentRequest.pull(inbox.content_id)
        progress_content_request = ProgressContentRequest.pull(content_request)
        content = get_content(content_request.content_type_id, content_request.content_id)
        progress_step = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                    status=30).order_by('step__step').last()
        first_approver = 0
        if progress_step is None:
            first_approver = 1
        account_list = content_request.content_request_account.all()
        date_str_list = content_request.get_start_to_end_date
        content_type = get_content_type_name(content.content_type['id'])

        if content_request.content_type_id == settings.CONTENT_TYPE('event.event').id:
            event_program_name = content.event_program.name if content.event_program else ''
            content_name = '%s (%s)' % (event_program_name, content.name)
            setattr(content, 'name', content_name)

        expire_detail = 1
        if settings.CONTENT_TYPE('public_learning.publiclearning').id == content_request.content_type_id:
            in_house = 0

        elif settings.CONTENT_TYPE('event.event').id == content_request.content_type_id:
            in_house = 0
            if progress_step and not progress_step.datetime_end or not progress_step:
                expire_detail = 0
        else:
            in_house = 1
            if progress_step and not progress_step.datetime_end or not progress_step:
                expire_detail = 0
        site = get_content_url(settings.CONTENT_TYPE('content_request.contentrequest').id, content_request.id)
        price = "{:,.2f}".format(content_request.price)
        return render_to_string(
            'mailer/inbox/request_for_approve.html',
            {
                'header_image': header_image,
                'content_request': content_request,
                'progress_step': progress_step,
                'progress_content_request': progress_content_request,
                'date_list': date_str_list,
                'account_list': account_list,
                'content': content,
                'content_type': content_type,
                'first_approver': first_approver,
                'expire_detail': expire_detail,
                'price': price,
                'site': site,
                'in_house': in_house
            }
        )

    elif inbox.type in [72]:  # Content Request
        content_request = ContentRequest.pull(inbox.content_id)
        progress_content_request = ProgressContentRequest.pull(content_request)
        progress_step = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                    status=30).order_by('step__step').last()
        progress_step_next = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                         status=1).first()
        content = get_content(content_request.content_type_id, content_request.content_id)

        if content_request.content_type_id == settings.CONTENT_TYPE('event.event').id:
            event_program_name = content.event_program.name if content.event_program else ''
            content_name = '%s (%s)' % (event_program_name, content.name)
            setattr(content, 'name', content_name)

        expire_detail = 1
        if settings.CONTENT_TYPE('public_learning.publiclearning').id == content_request.content_type_id:
            site = get_content_url(settings.CONTENT_TYPE('content_request.contentrequest').id, content_request.id)
        else:
            site = get_content_url(content_request.content_type_id, content_request.content_id)
            if progress_step_next and not progress_step_next.datetime_end or not progress_step_next:
                expire_detail = 0
        account_id_list = list(ProgressStep.objects.first().account_set.values_list('account_id', flat=True))
        # account_id_list = [5848, 5825, 99, 265]
        account_list = list(Account.objects.filter(id__in=account_id_list))
        return render_to_string(
            'mailer/inbox/content_request_result_step.html',
            {
                'header_image': header_image,
                'content_request': content_request,
                'progress_content_request': progress_content_request,
                'progress_step': progress_step,
                'progress_step_next': progress_step_next,
                'content': content,
                'account_list': account_list,
                'expire_detail': expire_detail,
                'site': site
            }
        )
    elif inbox.type in [75, 76, 77, 78, 79]:  # Content Request
        content_request = ContentRequest.pull(inbox.content_id)
        progress_step_list = ProgressStep.objects.filter(
            progress_content_request__content_request=content_request).order_by('step__step')
        progress_step = None
        if inbox.type == 76:
            progress_step = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                        status=-3).order_by('step__step').last()
        elif inbox.type == 77:
            progress_step = ProgressStep.objects.filter(progress_content_request__content_request=content_request,
                                                        status=-1).order_by('step__step').last()
        progress_content_request = ProgressContentRequest.pull(content_request)
        status = progress_content_request.status
        content = get_content(content_request.content_type_id, content_request.content_id)
        date_str_list = content_request.get_start_to_end_date
        content_type = get_content_type_name(content.content_type['id'])
        content = get_content(content_request.content_type_id, content_request.content_id)
        content_site = get_content_url(content.content_type['id'], content.id)

        if content_request.content_type_id == settings.CONTENT_TYPE('event.event').id:
            event_program_name = content.event_program.name if content.event_program else ''
            content_name = '%s (%s)' % (event_program_name, content.name)
            setattr(content, 'name', content_name)

        if settings.CONTENT_TYPE('public_learning.publiclearning').id == content_request.content_type_id:
            site = get_content_url(settings.CONTENT_TYPE('content_request.contentrequest').id, content_request.id)
            in_house = 0

        elif settings.CONTENT_TYPE('event.event').id == content_request.content_type_id:
            site = get_content_url(content_request.content_type_id, content_request.content_id)
            in_house = 0

        else:
            site = get_content_url(content_request.content_type_id, content_request.content_id)
            in_house = 1

        administrator = 0
        if inbox.type == 79:
            administrator = 1
        ptt_ess_email = Config.pull_value('ptt-ess-email')
        if ptt_ess_email:
            return render_to_string(
                '../../vendor_ptt/templates/inbox/content_request_result.html',
                {
                    'header_image': header_image,
                    'administrator': administrator,
                    'content_request': content_request,
                    'progress_step_list': progress_step_list,
                    'progress_step': progress_step,
                    'date_list': date_str_list,
                    'progress_content_request': progress_content_request,
                    'content': content,
                    'content_type': content_type,
                    'status': status,
                    'site': site,
                    'content_site': content_site,
                    'inhouse': in_house,
                }
            )
        else:
            return render_to_string(
                'mailer/inbox/content_request_result.html',
                {
                    'header_image': header_image,
                    'administrator': administrator,
                    'content_request': content_request,
                    'progress_step_list': progress_step_list,
                    'progress_step': progress_step,
                    'date_list': date_str_list,
                    'progress_content_request': progress_content_request,
                    'content': content,
                    'content_type': content_type,
                    'status': status,
                    'site': site,
                    'content_site': content_site,
                    'inhouse': in_house,
                }
            )
    elif inbox.type in [100]:  # Verification
        identity = IdentityVerification.objects.filter(id=inbox.content_id).first()
        if identity is None:
            return None

        site_url = Config.pull_value('config-site-url')
        verify_url = '%s/api/account/verify-email?token=%s' % (site_url, identity.token)
        app_name = Config.pull_value('config-app-name')
        return render_to_string(
            'mailer/inbox/email_verification.html',
            {
                'header_image': header_image,
                'app_name': app_name,
                'title': inbox.title,
                'body': inbox.body,
                'site_url': site_url,
                'verify_url': verify_url,
                'identity': identity,
                'button_color': Config.pull_value('config-login-button-color')
            }
        )
    else:
        return None


def get_subject(inbox):
    prefix = Config.pull_value('mailer-subject-prefix')
    if inbox.type == 1:
        return '%s You received new message' % prefix
    elif inbox.type == 2:
        return '%s You received News Updates' % prefix
    elif inbox.type == 10:
        return '%s You have new assignment' % prefix
    elif inbox.type == 11:
        return '%s Congratulations!, You have successfully enrolled' % prefix
    elif inbox.type == 12:
        return '%s Sorry, Your enrollment has been rejected' % prefix
    elif inbox.type in [20, 21, 22, 23]:
        transaction = Transaction.pull(inbox.content_id)
        content = get_content(transaction.content_type_id, transaction.content_id)
        return '%s Result of %s' % (prefix, getattr(content, 'name', transaction.content_type.app_label))
    elif inbox.type in [30, 31, 32]:
        content = get_content(inbox.content_type_id, inbox.content_id)
        return '%s Reminder for %s' % (prefix, getattr(content, 'name', inbox.content_type.app_label))
    elif inbox.type == 32:
        content = get_content(inbox.content_type_id, inbox.content_id)
        return '%s Sorry, %s has been canceled' % (prefix, getattr(content, 'name', inbox.content_type.app_label))
    elif inbox.type == 40:
        return '%s Congratulations!, Your E-Certificate has been approved' % prefix
    elif inbox.type == 41:
        return '%s Sorry, Your E-Certificate has been unapproved' % prefix
    elif inbox.type == 50:
        return '%s Congratulations!, Successfully checked-in' % prefix
    elif inbox.type == 51:
        return '%s Sorry, Checked-in failed' % prefix
    elif inbox.type in [60, 61, 62]:  # ProgressExam
        type_label = {
            60: 'Progress Exam Start',
            61: 'Progress Exam Announcement',
            62: 'Progress Exam Answer Key'
        }
        return 'Progress Exam %s Prefix' % type_label[inbox.type]
    elif inbox.type in [70, 71, 72, 73, 75, 76, 77, 78, 79]:
        step = None
        count_step = None
        if inbox.type == 72:
            content_request = ContentRequest.pull(inbox.content_id)
            progress_content_request = ProgressContentRequest.pull(content_request)
            count_step = progress_content_request.count_step
            step = progress_content_request.count_step_complete

        type_label = {
            70: 'You are in learner list',
            71: 'Request for your approval',
            72: 'Congratulations! Your request has been approved for step %s/%s' % (step, count_step),
            73: 'Your team member are in learner list of the public request',
            75: 'Congratulations! Your request has been approved for all steps.',
            76: 'Sorry, Your request has been rejected.',
            77: 'Sorry, Your request has expired.',
            78: 'Your request has been canceled by requester',
            79: 'Your request has been canceled by administrator'
        }
        return type_label[inbox.type] if inbox.type in type_label else '-'
    elif inbox.type in [100]:
        return '%s Please verify your email address' % prefix
    else:
        return prefix

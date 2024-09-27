from django.conf import settings
from django.test import TestCase

from account.tests import create_super_user, create_user
from course.models import Course
from .models import Inbox, Count


# class TestCaseInbox(TestCase):
#     def setUp(self):
#         self.content_type = settings.CONTENT_TYPE('assignment.assignment')
#
#         self.account_list = create_account_list()
#         self.content_list = create_content_list()
#         self.content = create_assignment(account_list=self.account_list, content_list=self.content_list)
#         self.content_id = self.content.id
#
#         self.type = 3
#         self.sender = self.content.account
#         self.title = 'Assignment to leaner'
#         self.body = 'Is Content good'
#
#     def test_push(self):
#         inbox = Inbox.push(receiver_list=self.account_list,
#                            sender=self.sender, type=self.type,
#                            content_list=self.content_list,
#                            content_type=self.content_type,
#                            content_id=self.content_id, title=self.title,
#                            body=self.body)
#         inbox.send_notification()
#         self.assertIsNotNone(inbox)
#         self.assertIsNotNone(inbox.content_set.exists())
#         self.assertIsNotNone(inbox.member_set.exists())
#         self.assertEqual(inbox.status, 1)
#

# class TestAPIInbox(TestCase):
#     def setUp(self):
#
#         self.content_type = settings.CONTENT_TYPE('assignment.assignment')
#
#         self.account_list = create_account_list()
#         self.content_list = create_content_list()
#         self.assignment = create_assignment(account_list=self.account_list, content_list=self.content_list)
#         account = create_user()
#         create_inbox_other(account=account, assignment=self.assignment)
#         self.client = APIClient()
#         self.client.force_authenticate(account)
#         self.bash_url = '/api/inbox/'
#
#     def test_get_list(self):
#         response = self.client.get(self.bash_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_post(self):
#         data = mock_data_read()
#         response = self.client.post(self.bash_url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class TestCountInbox(TestCase):
    def setUp(self):
        self.user = create_user()
        self.get_object = Count.objects.create(account=self.user)

    def test_method_pull(self):
        self.object = Count.pull(self.user)
        self.assertIsNotNone(self.object)

    def test_method_add(self):
        self.get_object.add()
        self.assertEqual(self.get_object.count, 1)

    def test_method_clear(self):
        self.get_object.add()
        count = Count.pull(self.user)
        count.clear_count()
        get_object = Count.objects.filter(account=self.user).first()
        self.assertEqual(get_object.count, 0)


def _transaction(content_type, content_id):
    from transaction.models import Transaction
    from django.utils import timezone
    from datetime import timedelta

    timezone_now = timezone.now()
    Transaction.objects.create(account=create_user(),
                               content_type=content_type,
                               content_id=content_id,
                               method=1,
                               datetime_start=timezone_now,
                               datetime_end=timezone_now + timedelta(hours=10))


def _mock_account_list():
    for index in range(0, 20):
        create_user()
    from account.models import Account
    return Account.objects.all()


def _mock_course():
    course_list = list()
    for index in range(1, 10):
        course_name = 'Course : %s' % index
        course = Course(name=course_name, is_display=True)
        course_list.append(course)

    Course.objects.bulk_create(course_list)


def create_account_list():
    account_list = list()
    for index in range(2):
        account_list.append(create_user())
    return account_list


def create_content_list():
    content_type_id = settings.CONTENT_TYPE('survey.survey').id
    from survey.models import Survey
    content_list = list()
    for index in range(2):
        name = 'Survey Number is %s ' % index
        survey = Survey.objects.create(name=name)
        content = {
            'content_id': survey.id,
            'content_type_id': content_type_id
        }
        content_list.append(content)
    return content_list


def create_assignment(account_list, content_list):
    from assignment.models import Assignment
    assignment = Assignment.objects.create(account=create_super_user(), status=4)

    for content in content_list:
        assignment.content_set.create(**content)

    for account in account_list:
        member = assignment.member_set.create(account=account)
        member.push_preview()

    return assignment


def create_inbox_other(account, assignment):
    content_type_assignment = settings.CONTENT_TYPE('assignment.assignment')
    title = 'Title'
    body = 'body'
    inbox_assignment = Inbox.objects.create(status=1,
                                            type=3,
                                            content_id=assignment.id,
                                            content_type=content_type_assignment,
                                            title=title,
                                            body=body)

    inbox_other = Inbox.objects.create(status=1, type=2, title=title, body=body)

    content_list = create_content_list()
    for content in content_list:
        # inbox_other.content_set.create(**content)
        inbox_assignment.content_set.create(**content)
    inbox_assignment.member_set.create(account=account)
    inbox_other.member_set.create(account=account)


def mock_data_read():
    data = {
        'channel': 1,
        'id_list': list(Inbox.objects.values_list('id', flat=True))
    }
    return data

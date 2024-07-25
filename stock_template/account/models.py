import datetime
import uuid

import six
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from parse import parse

from utils.encryption import AESCipher
from utils.model_fields import JSONField
from utils.model_permission import DEFAULT_PERMISSIONS
from utils.model_permission import VIEW_BY_PERMISSIONS


def generate_username():
    import random
    import string
    return ''.join(random.sample(string.ascii_lowercase, 6))


class AccountManager(BaseUserManager):

    def create_user(self, username, password):
        if username is None:
            raise ValueError('The given username must be set')

        user = self.model(
            username=username
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, is_accepted_active_consent=True):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """

        user = self.create_user(username, password)
        user.is_admin = True
        user.is_superuser = True
        user.type = 1
        user.is_accepted_active_consent = is_accepted_active_consent
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = (
        (0, 'Not set'),
        (1, 'Male'),
        (2, 'Female'),
        (3, 'Other'),
    )

    TYPE = (
        (0, 'user'),
        (1, 'system_user'),
    )

    LEARNINGPATH_VIEW_CHOICES = (
        (0, 'path_view'),
        (1, 'card_view'),
    )

    external_id = models.CharField(max_length=32, blank=True, null=True, default=None)
    code = models.CharField(max_length=32, db_index=True, blank=True, null=True, default=None)  # Employee id

    username_validator = UnicodeUsernameValidator() if six.PY3 else ASCIIUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )

    email = models.EmailField(
        verbose_name='Email address',
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=120, db_index=True, blank=True)
    middle_name = models.CharField(max_length=120, db_index=True, blank=True)
    last_name = models.CharField(max_length=120, db_index=True, blank=True)
    id_card = models.CharField(max_length=255, blank=True, null=True)  # Encrypt

    image = models.ImageField(upload_to='account/%Y/%m/', null=True, blank=True)
    image_log = models.ImageField(upload_to='account/%Y/%m/', null=True, blank=True)

    gender = models.IntegerField(choices=GENDER_CHOICES, default=0)
    type = models.IntegerField(choices=TYPE, default=0)
    language = models.CharField(max_length=12, blank=True, default='en')

    is_admin = models.BooleanField(default=False)

    # Mark remove
    uuid = models.CharField(max_length=120, blank=True, db_index=True)
    token = models.CharField(max_length=32, null=True, blank=True, db_index=True)

    desc = models.TextField(blank=True)

    phone = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    address = models.TextField(blank=True)

    last_active = models.DateTimeField(_('last active'), blank=True, null=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified_email = models.BooleanField(default=False)

    date_birth = models.DateField(null=True, blank=True)

    start_at = models.DateField(null=True, blank=True, default=timezone.now)
    end_at = models.DateField(null=True, blank=True)
    is_force_reset_password = models.BooleanField(default=False)

    datetime_update = models.DateTimeField(auto_now=True, null=True)

    working_location = models.CharField(max_length=255, blank=True)
    working_schedule_shift = models.CharField(max_length=255, blank=True)
    english_score = models.CharField(max_length=12, blank=True)
    learning_path_view = models.IntegerField(choices=LEARNINGPATH_VIEW_CHOICES, default=0)

    objects = AccountManager()

    USERNAME_FIELD = 'username'

    class Meta:
        default_permissions = DEFAULT_PERMISSIONS + VIEW_BY_PERMISSIONS + ('view_token', 'import', 'login_store', 'can_login_as')
        ordering = ['-is_active', '-id']

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def age(self):
        if self.date_birth:
            today = timezone.datetime.now()
            return today.year - self.date_birth.year - (
                    (today.month, today.day) < (self.date_birth.month, self.date_birth.day))
        elif int(self.count_age) != -1:
            return self.count_age
        return None

    @property
    def is_accepted_term(self):
        from term.models import Term
        term = Term.get_publish()
        if term:
            return term.is_consent_all(self.id)
        return True

    @property
    def is_accepted_privacy(self):
        from term.models import Privacy
        privacy = Privacy.get_publish()
        if privacy:
            return privacy.is_consent_all(self.id)
        return True

    @property
    def is_accepted_data_consent(self):
        from term.models import DataConsent
        data_consent = DataConsent.get_publish()
        if data_consent:
            return data_consent.is_consent_all(self.id)
        return True

    @property
    def service_experience(self):
        exp = None
        if self.date_start:
            today = timezone.datetime.now()
            exp = today.year - self.date_start.year - (
                    (today.month, today.day) < (self.date_start.month, self.date_start.day))
        elif int(self.count_service) != -1:
            exp = self.count_service
        return exp

    @property
    def work_experience(self):
        return self.count_experience

    @property
    def check_password_expire(self):
        from config.models import Config
        from datetime import timedelta
        from group.models import Account as GroupAccount

        if Config.pull_value('config-account-password-expire'):
            forgot = Forgot.objects.filter(account_id=self.id, status=2).order_by('-datetime_create').first()
            if forgot is None:
                password_create = self.date_joined
            else:
                password_create = forgot.datetime_create
            if GroupAccount.objects.filter(group__type='ACCOUNT_CUSTOM_1', group__code='new_external_agent',
                                           account_id=self.id).exists():
                days = Config.pull_value('config-account-age-password-extra').get('new_external_agent', 180)
            else:
                days = Config.pull_value('config-account-age-password')
            if days > 0 and timedelta(days=days) + password_create < timezone.now():
                return True
        return False

    @property
    def id_card_decrypt(self):
        from utils.encryption import AESCipher
        if self.id_card:
            if len(self.id_card) > 13:
                try:
                    return AESCipher(settings.SIGN_KEY).decrypt(self.id_card)
                except:
                    return ''
            else:
                return self.id_card
        return ''

    @property
    def is_dashboard_permission(self):
        return self.groups.filter(permissions__codename='view_dashboard').exists()

    @property
    def phone_country_code(self):
        from config.models import Config
        config = Config.pull_value('config-th-phone-number')

        if self.phone.startswith(config['country_code']):
            return self.phone

        return config['country_code'] + self.phone[-config['suffix_number_length']:]

    @staticmethod
    def pull(id):
        from .caches import cache_account
        return cache_account(id)

    # For Login # Active Account
    @staticmethod
    def pull_account(username_or_email):
        _account = Account.objects.filter(username=username_or_email, is_active=True).first()
        if _account is None:
            _account = Account.objects.filter(email=username_or_email, is_active=True).exclude(
                email__isnull=True).first()
        return _account

    @staticmethod
    def pull_account_data(id):
        from utils.redis import get_value
        from .utils_account_dict import get_account_dict
        import json
        _account = get_value('account_%s' % id)
        if _account is None:
            _account = get_account_dict(Account.pull(id), is_set=True)
            return _account
        return json.loads(_account) if _account else None

    @staticmethod
    def pull_account_from_key(key):
        _account = Account.objects.filter(code=key).first()
        if _account is None:
            _account = Account.objects.filter(username=key).first()
        if _account is None:
            _account = Account.objects.filter(email=key).first()
        return _account

    @staticmethod
    def pull_user_account_id_list():
        from .caches import cache_user_account_id_list
        return cache_user_account_id_list()

    @staticmethod
    def is_unique_code(code):
        if not code:
            return True
        return not Account.objects.filter(code=code).exclude(code__isnull=True).exists()

    @staticmethod
    def is_unique_username(username):
        if not username:
            return True
        return not Account.objects.filter(username=username).exclude(username__isnull=True).exists()

    @staticmethod
    def is_unique_email(email):
        if not email:
            return True
        return not Account.objects.filter(email=email).exclude(email__isnull=True).exists()

    @staticmethod
    def revoke_email(email):
        if email is None:
            return
        Account.objects.filter(email=email).update(email=None)

    @staticmethod
    def revoke_code(code):
        if code is None:
            return
        Account.objects.filter(code=code).update(code=None)

    def get_child_as_department_and_child_department_member_view(self):
        """
        2020917(NOOK): Change from list the member of same department to list the member of child department also.
        """
        from department.models import Department, Member
        department_list = Department.pull_by_account(self.id)
        department_id_set = {d.id for d in department_list}
        for department in department_list:
            _department_child = department.get_child_id_list()
            department_id_set = department_id_set.union(set(_department_child))
        member_id_list = Member.pull_member_by_multiple_department_id(list(department_id_set)).values_list(
            'account_id', flat=True)
        return set(member_id_list)

    def get_child_as_department_member_view(self):
        from department.models import Department, Member
        department_list = Department.pull_by_account(self.id).values_list('id', flat=True)
        member_id_list = Member.pull_member_by_multiple_department_id(department_list).values_list('account_id',
                                                                                                   flat=True)
        return set(member_id_list)

    def get_child_as_department_view(self):
        from department.models import Department, Admin

        department_list = Department.pull_by_account(self.id).values_list('id', flat=True)
        admin_list = Member.pull_member_by_multiple_department_id(
            department_list).values_list(
            'account__id', flat=True).distinct()
        return set(admin_list)

    def get_child_as_organization_view(self):
        from organization.models import Organization
        return set(Organization.get_child_by_account_id(self.id)).union(set([self.id]))

    def get_child_as_manager_view(self):
        from organization.models import Organization
        return set(
            Organization.objects.filter(parent_id=self.id).values_list('account__pk', flat=True).distinct()).union(
            set([self.id]))

    def get_log(self, mini=False):
        if mini:
            log = {
                'name': self.first_name + ' ' + self.last_name
            }
        else:
            log = {
                'code': self.code,
                'title': self.title,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'email': self.email,
                'gender': self.gender,
                'username': self.username,
                'image': self.image.name if self.image is not None else None,
                'language': self.language,
                'phone': self.phone,
                'supervisor': self.supervisor,
                'department': self.department,
                'date_joined': str(self.date_joined),
                'last_active': str(self.last_active),
                'is_active': self.is_active,
                'is_force_reset_password': self.is_force_reset_password,
            }
        return log

    def check_prolonged_active(self):
        from config.models import Config

        days = Config.pull_value('account-prolonged-active-days')
        if days > 0:
            if self.last_active:
                datetime_limit = self.last_active + timezone.timedelta(days=days)
            else:
                datetime_limit = self.date_joined + timezone.timedelta(days=days)

            if datetime_limit < timezone.now():
                return True

        return False


    def update_data(self):
        from organization.models import Organization
        from department.models import Department
        from account_position.models import Position
        from group.models import Group

        organization = Organization.objects.filter(account_id=self.id).select_related('parent').first()
        if organization:
            parent = organization.parent
            _supervisor = '%s %s %s' % (parent.title, parent.first_name, parent.last_name)
        else:
            _supervisor = '-'

        department_list = Department.objects.filter(member__account_id=self.id) \
            .values_list('name', flat=True).distinct()

        if len(department_list) > 0:
            _department = ', '.join(department_list)
        else:
            _department = '-'

        level = Group.objects.filter(type='ACCOUNT_LEVEL', account__account_id=self.id).first()
        if level:
            _level_name = level.name
        else:
            _level_name = '-'

        position_list = Position.objects.filter(member__account_id=self.id) \
            .order_by('member__department__name') \
            .values_list('name', flat=True) \
            .distinct()
        if len(position_list) > 0:
            _position = ', '.join(position_list)
        else:
            _position = '-'
        if self.supervisor != _supervisor or self.department != _department or self.position != _position or self.level_name != _level_name:
            self.supervisor = _supervisor
            self.department = _department
            self.position = _position
            self.level_name = _level_name
            self.save(update_fields=['supervisor', 'department', 'position', 'level_name'])

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def get_full_name(self):
        import re
        return re.sub(' +', ' ', '{0} {1} {2}'.format(self.first_name, self.middle_name, self.last_name))

    def forgot_password(self):

        from utils.generator import generate_token

        while True:
            token = generate_token(32)
            if not Forgot.objects.filter(token=token, method=1, status=1).exists():
                break

        Forgot.objects.create(
            account=self,
            token=token,
            method=1,
            status=1
        )
        return token

    def forgot_password_otp(self, send_method):

        from utils.otp import generate_otp

        while True:
            token = generate_otp()
            if not Forgot.objects.filter(account=self, token=token, method=4, status=1).exists():
                break

        forgot = Forgot.objects.create(
            account=self,
            token=token,
            send_method=send_method,
            method=4,
            status=1
        )
        return forgot

    def force_reset_password(self):
        from utils.generator import generate_token
        if not self.is_force_reset_password:
            self.is_force_reset_password = True
            self.save(update_fields=['is_force_reset_password'])
        method_status = 2
        Forgot.objects.filter(account_id=self.id, status=1, method=method_status).update(status=-1)
        forgot = Forgot.objects.create(account_id=self.id, status=1, method=method_status, token=generate_token(32))
        return forgot.token

    def get_token_reset_password(self, method, error, site='', device='WEB_'):
        from utils.generator import generate_token
        from log.models import Log
        from rest_framework import status
        forgot = None
        forgot_list = self.forgot_set.filter(method__in=[method], status=1)
        for _forgot in forgot_list:
            if not _forgot.is_token_expire:
                forgot = _forgot
                break
            else:
                if forgot.status != 3:
                    forgot.status = 3
                    forgot.save(update_fields=['status'])

        if forgot is None:
            method = 2
            Forgot.objects.filter(account_id=self.id, status=1, method=method).update(status=-1)
            forgot = Forgot.objects.create(account_id=self.id, status=1, method=method, token=generate_token(32))

        data = {
            'is_force_reset_password': True,
            'token': forgot.token,
            'method': forgot.method,
            'detail': error,
        }
        return data

    def get_auth_group_list(self):
        from .caches import cached_auth_group_list
        return cached_auth_group_list(self)

    def has_perm(self, perm, group=None, obj=None):
        if self.is_superuser and group is None:
            return True

        from .caches import cached_auth_permission

        def _get_permissions(user_obj, group):
            perms = cached_auth_permission(user_obj.id, group)
            return set("%s.%s" % (ct, name) for ct, name in perms)

        # Skip is_superuser
        if group is None:
            code = '_perm_cache'
        else:
            code = '_perm_cache_%s' % group.id
        if not hasattr(self, code):
            setattr(self, code, _get_permissions(self, group))
        return perm in getattr(self, code)

    def cache_delete(self):
        from .caches import cache_account_delete
        cache_account_delete(self.id)

    @staticmethod
    def cache_delete_all():
        from .tasks import task_update_all_user_cached
        task_update_all_user_cached.delay()


class Forgot(models.Model):
    STATUS_CHOICES = (
        (-1, 'Deactivate'),
        (1, 'Activate'),
        (2, 'Completed'),
        (3, 'Expired'),
    )

    METHOD_CHOICES = (
        (0, '(Not set)'),
        (1, 'Forgot password'),
        (2, 'Force reset password'),
        (3, 'Change password'),
        (4, 'Forgot password OTP'),
    )

    SENT_METHOD_CHOICE = (
        (1, 'Email'),
        (2, 'SMS')
    )

    REFERENCE_ID_FORMAT = '{id:d}'

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=120, db_index=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, db_index=True)
    method = models.IntegerField(choices=METHOD_CHOICES, default=0, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    send_method = models.IntegerField(choices=SENT_METHOD_CHOICE, default=1, db_index=True)
    count_failed = models.IntegerField(default=0)
    datetime_failed_limit = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()

    @property
    def reference_id(self):
        return self.REFERENCE_ID_FORMAT.format(id=self.id)

    @property
    def lifetime(self):
        second = Config.pull_value('config-account-forgot-password-otp-age')
        return second

    @property
    def is_token_expire(self):
        from datetime import timedelta
        from django.utils import timezone

        if self.method == 2:
            return False

        second = Config.pull_value('config-account-forgot-password-otp-age')
        day_offset = timedelta(seconds=second)
        is_expired = self.datetime_create + day_offset < timezone.now()
        if is_expired and self.status != 3:
            self.status = 3
            self.save(update_fields=['status'])
        return is_expired

    @property
    def is_failed_limit(self):
        failed_limit = Config.pull_value('config-account-forgot-password-otp-failed-limit')
        is_failed_limit = self.count_failed >= failed_limit
        return is_failed_limit

    @staticmethod
    def get_pk_by_reference(reference_id):
        parse_result = parse(Forgot.REFERENCE_ID_FORMAT, reference_id)
        if not parse_result:
            return None
        else:
            return parse_result['id']

    @staticmethod
    def update_count_failed(id):
        forgot = Forgot.objects.filter(id=id).first()
        is_failed_limit = False
        if forgot:
            failed_limit = Config.pull_value('config-account-forgot-password-otp-failed-limit')
            if forgot.count_failed < failed_limit:
                forgot.count_failed += 1
                if forgot.count_failed == failed_limit:
                    is_failed_limit = True
                    forgot.status = -1
                    forgot.datetime_failed_limit = timezone.now()
                forgot.save(update_fields=['count_failed', 'status', 'datetime_failed_limit'])
        return is_failed_limit

    def get_lifetime_text(self):
        m, s = divmod(self.lifetime, 60)
        h, m = divmod(m, 60)

        hour_str = ''
        minute_str = ''
        second_str = ''

        if h > 0:
            hour_str = '{!s} hours'.format(h)
        if m > 0:
            minute_str = '{!s} minutes'.format(m)
        if s > 0:
            second_str = '{!s} seconds'.format(s)

        return hour_str + minute_str + second_str

    def get_waiting_for_renew_countdown(self):
        from datetime import timedelta
        from django.utils import timezone

        second = Config.pull_value('config-account-forgot-password-otp-renew-delay')
        day_offset = timedelta(seconds=second)
        now = timezone.now()
        countdown = ((self.datetime_create + day_offset) - now).total_seconds()
        return countdown

    def get_banned_countdown(self):
        from datetime import timedelta
        from django.utils import timezone

        countdown = 0
        second = Config.pull_value('config-account-forgot-password-otp-banned-delay')
        day_offset = timedelta(seconds=second)
        now = timezone.now()
        if self.datetime_failed_limit:
            countdown = ((self.datetime_failed_limit + day_offset) - now).total_seconds()
        return countdown


class Session(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255, db_index=True)
    token = models.TextField(null=True, blank=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    @staticmethod
    def push(account, session_key, token=None):
        from importlib import import_module
        from django.conf import settings
        from config.models import Config
        from .caches import cache_account_delete

        is_single = Config.pull_value('account-login-single')
        if is_single:
            session_list = Session.objects.filter(account=account)
            if session_list:
                for session in session_list:
                    session_store = import_module(settings.SESSION_ENGINE).SessionStore
                    s = session_store(session_key=session.session_key)
                    s.delete()
                    session.delete()
        Session.objects.create(account=account, session_key=session_key, token=token)
        cache_account_delete(account.id)

    @staticmethod
    def remove(account_id, session_key=None):
        from importlib import import_module
        from django.conf import settings
        from config.models import Config
        from .caches import cache_account_delete

        is_single = Config.pull_value('account-login-single')
        session_store = import_module(settings.SESSION_ENGINE).SessionStore
        if is_single or session_key is None:
            for session in Session.objects.filter(account_id=account_id):
                _session = session_store(session.session_key)
                _session.delete()
                session.delete()
        else:
            for session in Session.objects.filter(account_id=account_id, session_key=session_key):
                _session = session_store(session.session_key)
                _session.delete()
                session.delete()
        cache_account_delete(account_id)


class PasswordHistory(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    password = models.CharField(_('password'), max_length=128)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()

    @staticmethod
    def check_password(account, password, old_password):
        def setter(password):
            account.set_password(password)
            # Password hash upgrades shouldn't be considered password changes.
            account._password = None
            account.save(update_fields=['password'])

        return check_password(password, old_password, setter)

    @staticmethod
    def check_exists(account, new_password):
        from config.models import Config
        limit_password = Config.pull_value('config-password-history')
        if limit_password > 0:
            password_history_list = PasswordHistory.objects.filter(
                account=account
            ).order_by('-datetime_create')[:limit_password]
            for old_password in password_history_list:
                if old_password.check_password(account, new_password, old_password.password):
                    return False
        return True


class Token(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    token = models.CharField(max_length=100, blank=True, unique=True)
    datetime_create = models.DateField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()
        ordering = ['-datetime_create']


class QrCode(models.Model):
    STATUS_CHOICES = (
        (-1, 'Deactivate'),
        (1, 'Activate'),
    )

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()
        ordering = ['-datetime_create']

    @staticmethod
    def set_deactivate(account):
        return QrCode.objects.filter(account=account, status=1).update(status=-1)

    @staticmethod
    def pull(id):
        return QrCode.objects.filter(id=id).first()

    @staticmethod
    def is_expired(account):
        from config.models import Config

        qr_code = QrCode.objects.filter(account=account)
        if qr_code.first() is not None:
            duration = timezone.now() - qr_code.first().datetime_create
            expiry_seconds = Config.pull_value('config-account-qr-code-expiry')
            if duration.total_seconds() > expiry_seconds:
                qr_code.update(status=-1)
                return True
            else:
                return False
        else:
            return None

    def get_code(self):
        return AESCipher(settings.SIGN_KEY).encrypt(str(self.id))

    @staticmethod
    def is_activate(qrcode):
        if qrcode.status == 1:
            return True
        else:
            return False


class SSOToken(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    sso_token = models.CharField(max_length=100, blank=True, unique=True)
    datetime_create = models.DateField(auto_now_add=True, db_index=True)
    is_active = models.BooleanField()

    class Meta:
        default_permissions = ()
        ordering = ['-datetime_create']

    @staticmethod
    def generate_token(account_id):
        sso_token = SSOToken.objects.create(account_id=account_id, sso_token=uuid.uuid4().hex, is_active=True)
        SSOToken.objects.filter(account_id=account_id).exclude(id=sso_token.id).update(is_active=False)
        return sso_token

    @classmethod
    def get_or_create_user_active_sso_token(cls, account_id):
        sso_token_object = SSOToken.objects.filter(account_id=account_id, is_active=True).first()
        if sso_token_object:
            return sso_token_object.sso_token
        else:
            sso_token_object = cls.generate_token(account_id)
            return sso_token_object.sso_token


class AbstractAccountCondition(models.Model):
    OPERATOR_CHOICE = (
        (1, 'match'),
        (2, 'does_not_match'),
    )

    # User
    department_list = models.TextField(blank=True, null=True)  # OR
    department_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    position_list = models.TextField(blank=True, null=True)  # OR
    position_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    level_list = models.TextField(blank=True, null=True)  # ACCOUNT_LEVEL
    level_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    level_group_list = models.TextField(blank=True, null=True)  # ACCOUNT_LEVEL_GROUP
    level_group_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    group_list = models.TextField(blank=True, null=True)  # OR # Group.objects.filter(type='ACCOUNT_GROUP')
    group_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    group_account_list = models.TextField(blank=True, null=True)  # OR ACCOUNT
    group_account_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    group_account_group_list = models.TextField(blank=True, null=True)  # Not use # replace with ACCOUNT_BU
    group_account_group_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    group_account_custom1_list = models.TextField(blank=True, null=True)  # ACCOUNT_CUSTOM_1
    group_account_custom1_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    group_account_custom2_list = models.TextField(blank=True, null=True)  # ACCOUNT_CUSTOM_2
    group_account_custom2_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    age_gte = models.SmallIntegerField(default=-1)
    age_lte = models.SmallIntegerField(default=-1)
    age_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    experience_gte = models.FloatField(default=-1)
    experience_lte = models.FloatField(default=-1)
    experience_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    level_year_gte = models.FloatField(default=-1)
    level_year_lte = models.FloatField(default=-1)
    level_year_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    service_gte = models.FloatField(default=-1)
    service_lte = models.FloatField(default=-1)
    service_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    level_group_year_gte = models.FloatField(default=-1)
    level_group_year_lte = models.FloatField(default=-1)
    level_group_year_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)

    date_account_start_gte = models.DateField(null=True, blank=True)
    date_account_start_lte = models.DateField(null=True, blank=True)
    date_account_operator = models.IntegerField(choices=OPERATOR_CHOICE, default=1)
    # END USER

    # Content
    course_dict = JSONField(default={})
    course_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    event_dict = JSONField(default={})
    event_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    event_program_dict = JSONField(default={})
    event_program_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    learning_program_dict = JSONField(default={})
    learning_program_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    onboard_dict = JSONField(default={})
    onboard_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    learning_path_dict = JSONField(default={})
    learning_path_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    exam_dict = JSONField(default={})
    exam_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    survey_dict = JSONField(default={})
    survey_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    activity_dict = JSONField(default={})
    activity_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    public_learning_dict = JSONField(default={})
    public_learning_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    category_dict = JSONField(default={})
    category_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    provider_dict = JSONField(default={})
    provider_operator = models.IntegerField(choices=OPERATOR_CHOICE, null=True, blank=True, default=1)

    datetime_create = models.DateTimeField(auto_now_add=True)
    datetime_update = models.DateTimeField(auto_now=True)

    # End content

    class Meta:
        abstract = True
        ordering = ['id']

    def get_summary(self):
        from .utils import account_queryset_filter
        return account_queryset_filter(
            None,
            department_list=self.department_list,
            department_operator=self.department_operator,
            position_list=self.position_list,
            position_operator=self.position_operator,
            level_list=self.level_list,
            level_operator=self.level_operator,
            level_group_list=self.level_group_list,
            level_group_operator=self.level_group_operator,
            group_list=self.group_list,
            group_operator=self.group_operator,
            group_account_list=self.group_account_list,
            group_account_operator=self.group_account_operator,
            group_account_custom1_list=self.group_account_custom1_list,
            group_account_custom1_operator=self.group_account_custom1_operator,
            group_account_custom2_list=self.group_account_custom2_list,
            group_account_custom2_operator=self.group_account_custom2_operator,
            age_gte=self.age_gte,
            age_lte=self.age_lte,
            age_operator=self.age_operator,
            experience_gte=self.experience_gte,
            experience_lte=self.experience_lte,
            experience_operator=self.experience_operator,
            level_year_gte=self.level_year_gte,
            level_year_lte=self.level_year_lte,
            level_year_operator=self.level_year_operator,
            level_group_year_gte=self.level_group_year_gte,
            level_group_year_lte=self.level_group_year_lte,
            level_group_year_operator=self.level_group_year_operator,
            service_gte=self.service_gte,
            service_lte=self.service_lte,
            service_operator=self.service_operator,
            date_account_start_gte=self.date_account_start_gte,
            date_account_start_lte=self.date_account_start_lte,
            date_account_operator=self.date_account_operator,
            course_dict=self.course_dict,
            course_operator=self.course_operator,
            event_dict=self.event_dict,
            event_operator=self.event_operator,
            event_program_dict=self.event_program_dict,
            event_program_operator=self.event_program_operator,
            learning_program_dict=self.learning_program_dict,
            learning_program_operator=self.learning_program_operator,
            onboard_dict=self.onboard_dict,
            onboard_operator=self.onboard_operator,
            learning_path_dict=self.learning_path_dict,
            learning_path_operator=self.learning_path_operator,
            exam_dict=self.exam_dict,
            exam_operator=self.exam_operator,
            survey_dict=self.survey_dict,
            survey_operator=self.survey_operator,
            activity_dict=self.activity_dict,
            activity_operator=self.activity_operator,
            public_learning_dict=self.public_learning_dict,
            public_learning_operator=self.public_learning_operator,
            category_dict=self.category_dict,
            category_operator=self.category_operator,
            provider_dict=self.provider_dict,
            provider_operator=self.provider_operator,
        )

    def reset(self):
        # account information
        self.department_list = None
        self.department_operator = 1
        self.position_list = None
        self.position_operator = 1
        self.level_list = None
        self.level_operator = 1
        self.level_group_list = None
        self.level_group_operator = 1
        self.group_list = None
        self.group_operator = 1
        self.group_account_list = None
        self.group_account_operator = 1
        self.group_account_custom1_list = None
        self.group_account_custom1_operator = 1
        self.group_account_custom2_list = None
        self.group_account_custom2_operator = 1
        self.age_gte = -1
        self.age_lte = -1
        self.age_operator = 1
        self.experience_gte = -1
        self.experience_lte = -1
        self.experience_operator = 1
        self.level_year_gte = -1
        self.level_year_lte = -1
        self.level_year_operator = 1
        self.level_group_year_gte = -1
        self.level_group_year_lte = -1
        self.level_group_year_operator = 1
        self.service_gte = -1
        self.service_lte = -1
        self.service_operator = 1
        self.date_account_start_gte = None
        self.date_account_start_lte = None
        self.date_account_operator = 1

        # account progress
        self.course_dict = {}
        self.course_operator = 1
        self.event_dict = {}
        self.event_operator = 1
        self.event_program_dict = {}
        self.event_program_operator = 1
        self.learning_program_dict = {}
        self.learning_program_operator = 1
        self.onboard_dict = {}
        self.onboard_operator = 1
        self.learning_path_dict = {}
        self.learning_path_operator = 1
        self.exam_dict = {}
        self.exam_operator = 1
        self.survey_dict = {}
        self.survey_operator = 1
        self.activity_dict = {}
        self.activity_operator = 1
        self.public_learning_dict = {}
        self.public_learning_operator = 1
        self.category_dict = {}
        self.category_operator = 1
        self.provider_dict = {}
        self.provider_operator = 1

        self.save()


def generate_token_field():
    token = uuid.uuid4().hex
    if IdentityVerification.objects.filter(token=token).exists():
        generate_token_field()
    return token


class IdentityVerification(models.Model):
    STATUS_CHOICES = (
        (-1, 'deactivate'),
        (1, 'activate'),
        (2, 'completed'),
        (3, 'expired'),
    )

    METHOD_CHOICES = (
        (0, 'not_set'),
        (1, 'email'),
        (2, 'phone_number')
    )

    SENT_METHOD_CHOICE = (
        (1, 'email'),
        (2, 'sms')
    )

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(unique=True, default=generate_token_field, max_length=120, db_index=True, editable=False)

    status = models.IntegerField(choices=STATUS_CHOICES, default=1, db_index=True)
    method = models.IntegerField(choices=METHOD_CHOICES, default=0, db_index=True)
    send_method = models.IntegerField(choices=SENT_METHOD_CHOICE, default=1, db_index=True)

    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    datetime_expire = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()

    @property
    def is_verify(self):
        if self.datetime_expire > timezone.now() and self.status == 1:
            return True
        else:
            self.status = 3
            self.save(update_fields=['status'])
            return False

    @staticmethod
    def send_verification(account, method, send_method):
        from inbox.tasks_push_email_verification import task_push_email_verification
        if account.is_verified_email:
            return False

        IdentityVerification.objects.filter(account_id=account.id, status=1).update(status=-1)
        expired_time = Config.pull_value('config-verification-expired-time')
        datetime_expire = timezone.now() + datetime.timedelta(minutes=int(expired_time))
        identity = IdentityVerification.objects.create(
            account_id=account.id, method=method, send_method=send_method, datetime_expire=datetime_expire
        )
        task_push_email_verification.delay(token=identity.token)
        return True


class OneTimePassword(models.Model):
    STATUS_CHOICES = (
        (-1, 'Deactivate'),
        (1, 'Activate'),
    )

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=10, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, db_index=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    datetime_expire = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()
        ordering = ['-datetime_create']

    def is_validate(account_id, otp_code):
        now = timezone.now()
        account = Account.pull(account_id)
        code = OneTimePassword.objects.filter(account=account, otp_code=otp_code, status=1,
                                              datetime_expire__gte=timezone.localtime(now)).first()
        if code is None:
            return False
        else:
            code.status = -1
            code.save(update_fields=['status'])
            return True

    def generate_otp_code(account):
        now = timezone.now()
        data = OneTimePassword.objects.filter(account=account, status=1,
                                              datetime_expire__gte=timezone.localtime(now)).first()
        if data is None:
            x = uuid.uuid4().int
            code = 'otp-' + str(x)[:6]
            datetime_expire = timezone.now() + datetime.timedelta(minutes=int(5))
            data = OneTimePassword.objects.create(account=account, otp_code=code, status=1,
                                                  datetime_expire=datetime_expire)
        return data


class Avatar(models.Model):
    image = models.ImageField(upload_to='account/avatar/%Y/%m/', null=True, blank=True)
    sort = models.IntegerField(db_index=True, default=0)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        default_permissions = ()
        ordering = ['sort', 'id']


class Ability(models.Model):
    code = models.CharField(max_length=150, unique=True)


class UserAbility(models.Model):
    account = models.ForeignKey('account.Account', on_delete=models.CASCADE)
    ability = models.ForeignKey('account.Ability', on_delete=models.CASCADE)

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
from django.utils.translation import gettext_lazy as _
from parse import parse

from utils.encryption import AESCipher
from utils.model_fields import JSONField
from utils.model_permission import DEFAULT_PERMISSIONS 


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
        default_permissions = DEFAULT_PERMISSIONS
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

    def force_reset_password(self):
        from utils.generator import generate_token
        if not self.is_force_reset_password:
            self.is_force_reset_password = True
            self.save(update_fields=['is_force_reset_password'])
        method_status = 2
        Forgot.objects.filter(account_id=self.id, status=1, method=method_status).update(status=-1)
        forgot = Forgot.objects.create(account_id=self.id, status=1, method=method_status, token=generate_token(32))
        return forgot.token

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

    @staticmethod
    def get_pk_by_reference(reference_id):
        parse_result = parse(Forgot.REFERENCE_ID_FORMAT, reference_id)
        if not parse_result:
            return None
        else:
            return parse_result['id']


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

class Session(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255, db_index=True)
    token = models.TextField(null=True, blank=True)
    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)


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
        expired_time = 15
        datetime_expire = timezone.now() + datetime.timedelta(minutes=int(expired_time))
        identity = IdentityVerification.objects.create(
            account_id=account.id, method=method, send_method=send_method, datetime_expire=datetime_expire
        )
        task_push_email_verification.delay(token=identity.token)
        return True

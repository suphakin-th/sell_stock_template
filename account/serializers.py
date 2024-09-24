import json
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoCoreValidationError
from django.core.files import File
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError, NotFound, APIException
from account.models import Account, Session, PasswordHistory, UserAbility
from utils.rest_framework.serializers import Base64ImageField
from utils.validators import validate_account_phone
from .models import Account, Forgot, QrCode
from django.utils import timezone


def check_email(value):
    if re.compile(r'[^@]+@[^@]+\.[^@]+').search(value):
        return True
    else:
        return False


def check_password(value):
    if re.compile('(?=.{8,})(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+|~=`{}:;<>?,.])').match(value):
        return True
    else:
        return False


class AccountAllSerializer(serializers.ModelSerializer):
    id_card = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Account
        exclude = ['password',
                   'user_permissions',
                   'last_login',
                   'extra',
                   'image',
                   'uuid',
                   'is_admin',
                   'is_force_reset_password',
                   ]

    def get_id_card(self, account):
        return account.id_card_decrypt

    def get_gender(self, account):
        return account.get_gender_display()

    def get_is_active(self, account):
        return 'Active' if account.is_active else 'Inactive'


class AccountListMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'first_name',
            'last_name',
            'image',
        )


class AccountListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'title',
            'first_name',
            'last_name',
            'email',
            'username',
            'image',
        )


class LoginAsSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    qr = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            'id',
            'code',
            'username',
            'email',
            'name',
            'qr'
        )

    def get_name(self, account):
        return account.get_full_name()

    def get_qr(self, account):
        is_expired = QrCode.is_expired(account)
        if is_expired:
            QrCode.set_deactivate(account)
        elif is_expired is None:
            pass

        serializer = QrCodeSerializer(data={})
        serializer.is_valid(raise_exception=True)
        qr_code = serializer.save(account=account)
        _code = qr_code.get_code()
        return _code


def send_reset_password(account):
    token = account.force_reset_password()
    email = account.email
    site_url = Config.pull_value('config-site-url')
    ForgetPasswordUser.create_forget_user_password(email, token, site_url, method=2)


class AccountResetPassword(serializers.Serializer):
    id = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    is_force_reset_password = serializers.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conditions = []
        values = Config.pull_value('config-account-condition-password')
        if values:
            for key_condition in values:
                data = {}
                value = values[key_condition]
                if value['is_use']:
                    condition = value['compile']
                    name = value['name']
                    data['condition'] = condition
                    data['name'] = name
                    self._conditions.append(data)

    def save(self, **kwargs):
        validated_data = dict(list(self.validated_data.items()) + list(kwargs.items()))
        return self.create(validated_data)

    def create(self, validated_data):
        id_list = validated_data.get('id')
        is_force_reset_password = validated_data.get('is_force_reset_password')
        password = validated_data.get('new_password')

        account_list = Account.objects.filter(id=id_list)
        for account in account_list:
            if is_force_reset_password:
                account.set_password(password)
                account.is_force_reset_password = True
                send_reset_password(account)
            else:
                account.set_password(password)
                account.is_force_reset_password = False
                _status = 2
                method = 3
                token = generate_token(32)
                account.forgot_set.create(status=_status, method=method, token=token)
                account.last_active = timezone.now()
            Log.push(None, 'ACCOUNT', 'RESET_PASSWORD', account, 'User password ', status.HTTP_200_OK)
            PasswordHistory.objects.create(account=account, password=account.password)
            account.save(update_fields=['password', 'is_force_reset_password', 'last_active'])

        return account_list

    def validate(self, data):
        if data["new_password"] == data["confirm_password"]:
            return data
        else:
            raise ValidationError('Your password does not match.')

    def validate_new_password(self, value):
        message_error = list()
        for data in self._conditions:
            if re.compile(data.get('condition')).search(value) is None:
                message_error.append(data.get('name'))
        request = self.context.get('request')
        ids = request.data['id']
        acc_list = Account.objects.filter(id=ids)
        if len(acc_list) < 1:
            message_error.append('not found this id in system.')
            raise ValidationError(message_error)
        for acc in acc_list:
            check_password = PasswordHistory.check_exists(acc, value)
            if not check_password:
                message_error.append('error_password_must_differ')
        if message_error.__len__() > 0:
            raise ValidationError(list(set(message_error)))
        return value

    def validate_confirm_password(self, value):
        message_error = list()
        for data in self._conditions:
            if re.compile(data.get('condition', None)).search(value) is None:
                message_error.append(data.get('name', None))
        if message_error.__len__() > 0:
            raise ValidationError(message_error)
        return value

    def validate_id(self, value):
        if len(value) < 1:
            raise ValidationError('Please select at least 1 account to change password.')
        else:
            request = self.context.get('request')
            if (not Account.objects.filter(id=value).exists()) or (str(request.user.id) != str(value)):
                raise NotFound('Account not found.')
            else:
                return value


class AccountSerializer(serializers.ModelSerializer):
    image = Base64ImageField(allow_empty_file=True, allow_null=True, required=False)
    department = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    notification_count = serializers.SerializerMethodField()
    force_token = serializers.SerializerMethodField()
    id_card = serializers.SerializerMethodField()
    is_store_permission = serializers.SerializerMethodField()
    is_verified_email = serializers.SerializerMethodField()
    is_system_user = serializers.SerializerMethodField()
    is_team_dashboard = serializers.SerializerMethodField()
    payload = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            'id',
            'title',
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'phone',
            'image',
            'language',
            'department',
            'position',
            'notification_count',
            'date_joined',
            'date_birth',
            'age',
            'date_start',
            'work_experience',
            'level_group',
            'level_name',
            'code',
            'code2',
            'username',
            'id_card',
            'last_active',
            'is_active',
            'is_force_reset_password',
            'force_token',
            'is_dashboard_permission',
            'is_accepted_active_consent',
            'is_accepted_term',
            'is_accepted_privacy',
            'is_accepted_data_consent',
            'is_superuser',
            'is_subscribe',
            'is_store_permission',
            'is_system_user',
            'is_verified_email',
            'company',
            'is_team_dashboard',
            'learning_path_view',
            'payload',
            'is_creator',
        )
        read_only_fields = ('date_joined',
                            'last_active',
                            'is_active',
                            'force_token',
                            'is_accepted_active_consent',
                            'is_superuser',)

    def get_department(self, account):
        department = Department.objects.filter(member__account=account).first()
        return department.name if department else None

    def get_position(self, account):
        member = Member.objects.filter(account=account).select_related('position').first()
        return member.position.name if member and member.position else None

    def get_notification_count(self, account):
        count = cache_account_count(account)
        return count.count

    def get_id_card(self, account):
        return account.id_card_decrypt

    def get_force_token(self, account):  # TODO: remove
        if int(Config.pull_value('config-login-backend')) == 0:
            if account.is_force_reset_password:
                forgot = account.forgot_set.filter(method=2).first()
                if forgot is None:
                    return account.forgot_password()
                else:
                    return forgot.token
        return ''

    def get_is_store_permission(self, account):
        if account.username in Config.pull_value('config-login-store') or account.email in Config.pull_value(
                'config-login-store'):
            return True
        else:
            return False

    def get_is_verified_email(self, account):
        if Config.pull_value('config-verify-email-is-enabled'):
            return account.is_verified_email
        return True

    def get_is_system_user(self, account):
        if account.type == 1:
            return True
        return False
    
    def get_is_team_dashboard(self, account):
        account_set = account.get_child_as_manager_view() - {account.id}
        if len(account_set) > 0:
            is_team_dashboard = True
        else:
            is_team_dashboard = False
        return is_team_dashboard

    def get_payload(self, account):
        payload = None
        if Config.pull_value('config-account-encrypt-payload-is-enabled'):
            secret = Config.pull_value('config-account-encrypt-payload-secret')
            data = AccountPayloadSerializer(account).data
            payload = AESCipherADA(secret).encrypt(json.dumps(data))
        return payload

    def get_is_creator(self, account):
        is_creator = UserAbility.objects.filter(
            account_id=account.id,
            ability__code='creator'
        ).exists()
        return is_creator


class UserDetailSerializer(serializers.ModelSerializer):
    image = Base64ImageField(allow_empty_file=True, allow_null=True, required=False)
    last_update = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            'id',
            'is_active',
            'last_active',
            'department',
            'position',
            'level_group',
            'level_name',
            'date_joined',
            'date_start',
            'last_update',
            'address',
            'age',
            'image',
            'is_subscribe',
            'supervisor',
            'is_creator',
        )

    def get_department(self, account):
        department_member = Member.pull_list(account).first()
        if department_member is None:
            return None
        return DepartmentDetailSerializer(department_member.department).data

    def get_supervisor(self, account):
        supervisor = Organization.objects.filter(account_id=account.id).first()
        if supervisor:
            return AccountListSerializer(supervisor.parent).data
        else:
            return None

    def get_last_update(self, account):
        last_update = Forgot.objects.filter(account=account, status=2).order_by('-datetime_create').first()
        return convert_to_local(last_update.datetime_create) if last_update else None

    def to_representation(self, account):
        ret = super().to_representation(account)
        default_config_data = DEFAULT_CONFIG_DICT
        config_data = Config.pull_value('config-register-form')
        field_list = []

        if config_data:
            if account.extra not in ['', '{}']:
                extra = json.loads(account.extra)
            else:
                extra = {}

            field_list = config_data.get('field_list', [])
            for config in field_list:
                is_editable = config.get('is_editable', False)
                if config.get('key') == 'password':
                    data = ''
                elif config.get('key') == 'id_card':
                    data = account.id_card_decrypt
                elif config.get('key', '')[0:12] == 'custom_field':
                    data = extra.get(config.get('key'))
                else:
                    data = getattr(account, config.get('key'), None)
                if config.get('condition_list'):
                    config.pop('condition_list')

                config.update({'data': data, 'is_editable': is_editable})
                if config.get('key') in default_config_data:
                    default_config_data.pop(config.get('key'))

        for key in default_config_data:
            _data = default_config_data[key]
            if key == 'password':
                data = ''
            elif key == 'id_card':
                data = account.id_card_decrypt
            elif key == 'gender':
                choice_list = []
                gender_choices_dict = dict(Account.GENDER_CHOICES)
                gender_choices_dict.pop(0)

                for k, v in gender_choices_dict.items():
                    choice_list.append({'name': v.lower(), 'value': k})

                _data['choice_list'] = choice_list
                data = getattr(account, key, None)
            else:
                data = getattr(account, key, None)

            data_dict = {**_data, 'data': data}
            field_list.append(data_dict)

        del default_config_data
        ret.update({'field_list': field_list})
        return ret

    def get_notification_count(self, account):
        count = cache_account_count(account)
        return count.count

    def get_id_card(self, account):
        return account.id_card_decrypt if account.id_card_decrypt not in ['', '-', None] else None

    def get_is_store_permission(self, account):
        if account.username in Config.pull_value('config-login-store') or account.email in Config.pull_value(
                'config-login-store'):
            return True
        else:
            return False

    def get_is_verified_email(self, account):
        if Config.pull_value('config-verify-email-is-enabled'):
            return account.is_verified_email
        return True

    def get_is_creator(self, account):
        is_creator = UserAbility.objects.filter(
            account_id=account.id,
            ability__code='creator'
        ).exists()
        return is_creator


class UserUpdateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(allow_empty_file=True, allow_null=True, required=False)
    image_log = Base64ImageField(allow_empty_file=True, allow_null=True, required=False, write_only=True)
    count_experience_year = serializers.IntegerField(required=False, allow_null=True)
    count_experience_month = serializers.IntegerField(required=False, allow_null=True)
    extra = serializers.DictField(default={}, required=False, allow_null=True)
    is_upload_avatar = serializers.BooleanField(required=False, allow_null=True)

    class Meta:
        model = Account
        fields = (
            'id',
            'title',
            'first_name',
            'middle_name',
            'last_name',
            'gender',
            'phone',
            'address',
            'email',
            'image',
            'image_log',
            'date_birth',
            'age',
            'level_group',
            'level_name',
            'code',
            'code2',
            'id_card',
            'last_active',
            'is_active',
            'is_subscribe',
            'company',
            'count_experience_year',
            'count_experience_month',
            'avatar',
            'extra',
            'is_upload_avatar',
        )

    def to_internal_value(self, data):
        import re

        extra = {}
        for key in data:
            regex = re.compile(r'(custom_field_)[\d]+')
            if bool(regex.match(key)):
                extra[key] = data[key]

        if len(extra):
            data['extra'] = extra
        if 'gender' in data and isinstance(data['gender'], str):
            if data['gender'] == 'Male':
                data['gender'] = 1
            elif data['gender'] == 'Female':
                data['gender'] = 2
            elif data['gender'] == 'Other':
                data['gender'] = 3
            else:
                data['gender'] = 0
        return super().to_internal_value(data)

    def update(self, account, validated_data):
        if 'image_log' in validated_data and validated_data['image_log']:
            validated_data.pop('image_log')

        if 'image' in validated_data and validated_data.get('is_upload_avatar') is True:
            # upload new avatar
            if validated_data['image']:
                validated_data['avatar'] = None
                validated_data['image_log'] = validated_data['image']
        elif 'avatar' in validated_data and validated_data.get('is_upload_avatar') is False:
            # upload default avatar
            avatar = validated_data['avatar']
            if avatar:
                if not account.image_log and account.image:
                    validated_data['image_log'] = account.image.name
                account.image = avatar.image.name
            if 'image' in validated_data and validated_data['image']:
                validated_data.pop('image')
        elif 'is_upload_avatar' in validated_data and validated_data.get('is_upload_avatar') is False:
            # upload existing avatar
            if account.image_log:
                validated_data['avatar'] = None
                account.image = account.image_log.name
            if 'image' in validated_data and validated_data['image']:
                validated_data.pop('image')

        for field in self.fields:
            if field in validated_data:
                setattr(account, field, validated_data.get(field))

        return super().update(account, validated_data)


class MiniAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'id',
            'title',
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'language',
            'department',
            'position',
            'date_birth',
            'age',
            'work_experience',
            'level_group',
            'level_name',
            'code',
            'code2',
        )


class MiniAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            'id',
            'title',
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'language',
            'department',
            'position',
            'date_birth',
            'age',
            'work_experience',
            'level_group',
            'level_name',
            'code',
            'code2',
        )

class CreatedbyAccountSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            'id',
            'name',
            'image'
        )

    def get_name(self, account):
        return account.get_full_name()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(allow_empty_file=True, allow_null=True, required=False)
    count_experience_year = serializers.IntegerField(required=False, allow_null=True)
    count_experience_month = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Account
        fields = ('title', 'first_name', 'last_name', 'image', 'language', 'company', 'count_experience_year',
                  'is_subscribe', 'count_experience_month')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=settings.PASSWORD_MIN)
    is_remember = serializers.BooleanField(default=True)
    language = serializers.CharField(max_length=24, allow_blank=True, required=False, default='en')
    is_main_login = serializers.BooleanField(allow_null=True, required=False)

    def send_reset_password(self, account):
        token = account.force_reset_password()
        email = account.email
        site_url = Config.pull_value('config-site-url')
        ForgetPasswordUser.create_forget_user_password(email, token, site_url, method=2)
        return token

    def validate_password(self, value):
        if len(value) < settings.PASSWORD_MIN:
            raise ValidationError('Language not in Config')
        else:
            return value

    def validate_language(self, value):
        _default_value = Config.pull_value('config-default-language')
        _config_value = Config.pull_value('config-locale')
        if not value:
            return _default_value
        else:
            if value in _config_value:
                return value
            else:
                raise ValidationError('Language not in Config')

    def validate_username(self, value):
        key_login = Config.pull_value('account-login-key')
        value = value.encode('ascii', 'ignore').decode('utf-8')
        if 'email' in key_login and 'or' not in key_login:
            if not check_email(value):
                raise ValidationEmailError('incorrect_email_format')

        return value


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)


class ForgetPasswordOTPSerializer(serializers.ModelSerializer):
    username_or_email = serializers.CharField(max_length=255, write_only=True)
    reference_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Forgot
        fields = (
            'username_or_email',
            'send_method',
            'reference_id',
        )

    def get_reference_id(self, forgot):
        return forgot.reference_id


class ResendForgetPasswordOTPSerializer(serializers.ModelSerializer):
    send_method = serializers.IntegerField(read_only=True)
    reference_id = serializers.CharField()

    class Meta:
        model = Forgot
        fields = (
            'send_method',
            'reference_id',
        )


class AccountForgetPasswordOTPSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    phone = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Account
        fields = (
            'email',
            'phone'
        )

    def get_email(self, account):
        ANONYMIZE_EMAIL_SHOW_DIGITS = 1
        ANONYMIZE_EMAIL_HIDDEN_CHARACTER = 'x'

        if not account.email:
            return None

        # split email
        email_splited = account.email.split('@')
        email_name, email_host = (email_splited[0], email_splited[1])

        # create anonymize email
        anonymize_email = email_name[:ANONYMIZE_EMAIL_SHOW_DIGITS]
        anonymize_email += ''.join(
            [ANONYMIZE_EMAIL_HIDDEN_CHARACTER for i in
             range(len(email_name[ANONYMIZE_EMAIL_SHOW_DIGITS:]) - ANONYMIZE_EMAIL_SHOW_DIGITS)]
        )
        anonymize_email += email_name[-ANONYMIZE_EMAIL_SHOW_DIGITS]
        anonymize_email += '@' + email_host

        return anonymize_email

    def get_phone(self, account):

        ANONYMIZE_PHONE_PREFIX_SHOW_DIGITS = 0
        ANONYMIZE_PHONE_SUFFIX_SHOW_DIGITS = 4
        ANONYMIZE_PHONE_HIDDEN_CHARACTER = 'x'

        if not account.phone:
            return None

        try:
            validate_account_phone(account.phone)
        except DjangoCoreValidationError:
            return None

        anonymize_phone = account.phone[:ANONYMIZE_PHONE_PREFIX_SHOW_DIGITS]
        anonymize_phone += ''.join(
            [ANONYMIZE_PHONE_HIDDEN_CHARACTER for i in range(
                len(
                    account.phone[ANONYMIZE_PHONE_PREFIX_SHOW_DIGITS:-ANONYMIZE_PHONE_SUFFIX_SHOW_DIGITS]
                )
            )
             ]
        )
        anonymize_phone += account.phone[-ANONYMIZE_PHONE_SUFFIX_SHOW_DIGITS:]
        return '%s-%s-%s' % tuple(re.findall(r'\w{4}$|\w{3}', anonymize_phone))


class ValidateSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    token = serializers.CharField(required=False)


class OauthValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    is_web = serializers.BooleanField(default=True)


class OauthNotificationLogoutSerializer(serializers.Serializer):
    access_tokens = serializers.ListSerializer(child=serializers.CharField(), required=True)
    action = serializers.CharField(required=True)


class SSOSerializer(serializers.Serializer):
    authorization_code = serializers.CharField(max_length=255)


class SSORedirectSerializer(serializers.Serializer):
    return_path = serializers.CharField(max_length=255, required=False)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    confirm_password = serializers.CharField(required=False)
    email = serializers.CharField(max_length=255, required=False)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_subscribe = serializers.BooleanField(default=True, required=False)
    is_term_and_condition = serializers.BooleanField(default=True, required=False)
    is_accepted_active_consent = serializers.BooleanField(default=False, required=False)
    is_accepted_term = serializers.BooleanField(default=False, required=False)
    is_accepted_privacy = serializers.BooleanField(default=False, required=False)
    id_card = serializers.CharField(max_length=255, required=False, allow_blank=True)
    code = serializers.CharField(max_length=32, required=False, allow_blank=True)
    code2 = serializers.CharField(max_length=32, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date_birth = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    count_experience = serializers.DictField(default={}, required=False, allow_null=True)

    # def validate_is_accepted_active_consent(self, value):
    #     if not value and Term.objects.filter(content_type_id=settings.CONTENT_TYPE('term.term').id,
    #                                          is_publish=True).exists():
    #         raise serializers.ValidationError('please_accept_terms_condition')
    #     return value

    # def validate(self, attrs):
    #     message_error = list()
    #     config_value = Config.pull_value('config-account-condition-password')
    #     if config_value:
    #         for key_condition in config_value:
    #             _ = config_value[key_condition]
    #             if _['is_use']:
    #                 if re.compile(_['compile']).search(attrs['new_password']) is None:
    #                     message_error.append(_['name'])
    #     id = Forgot.get_pk_by_reference(attrs['reference_id'])
    #     forgot = Forgot.objects.filter(
    #         id=id,
    #         token=attrs['token'],
    #         method=attrs['method'],
    #         status=1
    #     ).first()
    #     if forgot:
    #         check_password = PasswordHistory.check_exists(forgot.account, attrs['new_password'])
    #         if not check_password:
    #             message_error.append('error_password_must_differ')
    #     if attrs['new_password'] != attrs['confirm_password']:
    #         message_error.append('password_not_match')
    #     if message_error.__len__() > 0:
    #         raise ValidationError({'new_password': message_error})
    #     return attrs


class LoginSocialSerializer(serializers.Serializer):
    social_type = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=9999)


class AccountNameSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            'id',
            'name',
            'image'
        )

    def get_name(self, account):
        return account.get_full_name()


class ValidationEmailError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = {'detail': 'incorrect_email_format'}


class AccountInactiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('id','is_active')


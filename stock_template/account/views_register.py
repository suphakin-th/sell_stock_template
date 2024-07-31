import json

from django.contrib.auth import login
from django.conf import settings
from django.core.validators import validate_email, ValidationError
from django.utils import timezone
from rest_framework import mixins
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotAcceptable
from analytic.models import Session2 as AnalyticSession
from config.models import Config
from content_permission.models import Condition
from log.models import Log
from om.utils import get_gender
from register_profile.register import Register
from utils.ip import get_client_ip
from utils.response import Response
from .models import Account, Session
from .models import IdentityVerification
from .serializers import RegisterSerializer, AccountSerializer
from term.models import Term, Consent, Privacy, PrivacyConsent


def register(request, data, is_web):
    config_register_value = Config.pull_value('config-register-form')
    all_field = config_register_value['field_list']

    database_standard_field = {
        'username', 'email', 'password', 'confirm_password', 'title', 'first_name',
        'last_name', 'gender', 'date_birth', 'address',
        'phone', 'is_term_and_condition', 'is_subscribe', 'is_accepted_active_consent',
        'is_accepted_term', 'is_accepted_privacy',
        'code', 'code2', 'middle_name', 'id_card', 'company', 'count_experience'
    }
    param_extra_field = {}
    # Check Empty Field
    for field in all_field:
        if not field['is_optional']:
            if field['key'] not in data:
                return {'detail': '%s_is_required' % field['key']}, status.HTTP_428_PRECONDITION_REQUIRED

        value = data.get(field['key'])
        if field['key'] in data and value and field['key'] not in str(database_standard_field):
            param_extra_field[field['key']] = value

        min_length = field.get('min_length')
        max_length = field.get('max_length')
        if min_length and value and len(value) < int(min_length) and max_length is None:
            return {'detail': '%s_length_error' % field['key']}, status.HTTP_400_BAD_REQUEST
            # return {'detail': '%s_must_be_more_than_%s_characters' % (field['key'], min_length)}, \
            #        status.HTTP_400_BAD_REQUEST
        if max_length and value and len(value) > int(max_length) and min_length is None:
            return {'detail': '%s_length_error' % field['key']}, status.HTTP_400_BAD_REQUEST
            # return {'detail': '%s_must_be_less_than_%s_characters' % (field['key'], max_length)}, \
            #        status.HTTP_400_BAD_REQUEST
        if max_length and value and len(value) > int(max_length) or min_length and value and len(value) < int(
                min_length):
            return {'detail': '%s_length_error' % field['key']}, status.HTTP_400_BAD_REQUEST
            # return {'detail': '%s_must_be_%s_to_%s_characters' % (field['key'], min_length, max_length)}, \
            #        status.HTTP_400_BAD_REQUEST

    username = Account.objects.filter(username__iexact=data.get('username', '').strip()).first()
    if username:
        return {'detail': 'username_has_been_already_use'}, status.HTTP_409_CONFLICT
    if data.get('email'):
        email = Account.objects.filter(email__iexact=data.get('email', '').strip()).first()
        if email:
            return {'detail': 'email_has_been_already_use'}, status.HTTP_409_CONFLICT
        try:
            validate_email(data.get('email'))
        except ValidationError:
            return {'detail': 'error_email_format'}, status.HTTP_400_BAD_REQUEST

    # if len(data['password']) < 8:
    #     return {'detail': 'Password must be minimum 8 characters'}, status.HTTP_400_BAD_REQUEST

    # if not check_password(data['password']):
    #     return {'detail': 'Invalid Password'}, status.HTTP_400_BAD_REQUEST
    if data.get('confirm_password'):
        if data.get('password') != data.get('confirm_password'):
            return {'detail': 'password_not_match'}, status.HTTP_400_BAD_REQUEST

    # if 'is_term_and_condition' in data:
    #     if not data['is_term_and_condition']:
    
    # if not data.get('is_accepted_privacy', False) and bool(Privacy.get_publish()):
    #     return {'detail': 'please_accept_privacy'}, status.HTTP_400_BAD_REQUEST

    # _privacy = Privacy.get_publish()
    # is_publish_privacy = bool(_privacy)
    # _is_accept_privacy = True if not is_publish_privacy else data.get('is_accepted_privacy', False)

    if not data.get('is_accepted_privacy', False) and bool(Privacy.get_publish()):
        return {'detail': 'please_accept_privacy'}, status.HTTP_400_BAD_REQUEST

    _privacy = Privacy.get_publish()
    is_publish_privacy = bool(_privacy)
    _is_accept_privacy = True if not is_publish_privacy else data.get('is_accepted_privacy', False)

    is_term_and_condition = data.get('is_term_and_condition', True)
    if not is_term_and_condition:
        return {'detail': 'please_accept_terms_condition'}, status.HTTP_428_PRECONDITION_REQUIRED

    # if not data.get('is_accepted_active_consent', False) and bool(Term.get_publish()):
    #     return {'detail': 'please_accept_terms_condition'}, status.HTTP_400_BAD_REQUEST

    # _term = Term.get_publish()
    # is_publish_term = bool(_term)
    # _is_accept_active_consent = True if not is_publish_term else data.get('is_accepted_active_consent', False)

    if not data.get('is_accepted_term', False) and bool(Term.get_publish()):
        return {'detail': 'please_accept_terms_condition'}, status.HTTP_400_BAD_REQUEST

    _term = Term.get_publish()
    is_publish_term = bool(_term)
    _is_accept_active_consent = True if not is_publish_term else data.get('is_accepted_term', False)

    try:
        param_extra_field = json.dumps(param_extra_field)
    except:
        pass

    count_experience_dict = data.get('count_experience')
    if count_experience_dict:
        count_experience_year = count_experience_dict.get('count_experience_year')
        count_experience_month = count_experience_dict.get('count_experience_month')
        if count_experience_year is None and count_experience_month is None:
            count_experience = -1
        elif count_experience_year is None:
            count_experience = count_experience_month
        elif count_experience_month is None:
            count_experience = (count_experience_year * 12)
        else:
            count_experience = (count_experience_year * 12) + count_experience_month
    else:
        count_experience = -1

    _account = Account.objects.create(
        username=data.get('username', '').strip(),
        email=data.get('email', '').strip().lower() if data.get('email') else None,
        title=data.get('title', ''),
        first_name=data.get('first_name', ''),
        middle_name=data.get('middle_name', ''),
        last_name=data.get('last_name', ''),
        gender=get_gender(data.get('gender', 0)),
        date_birth=data.get('date_birth') if data.get('date_birth') else None,
        address=data.get('address', ''),
        phone=data.get('phone', ''),
        is_term_and_condition=is_term_and_condition,
        is_subscribe=data.get('is_subscribe', True),
        extra=param_extra_field,
        date_start=None,
        is_accepted_active_consent=_is_accept_active_consent,
        # is_accepted_privacy=_is_accept_privacy,
        id_card=data.get('id_card', ''),
        code=data.get('code', ''),
        code2=data.get('code2'),
        company=data.get('company', ''),
        count_experience=count_experience,
    )
    if _is_accept_privacy and is_publish_privacy:
        # PrivacyConsent.objects.create(account=_account, privacy=_privacy)
        _privacy.consent(_account.id, True)
    
    if _is_accept_active_consent and is_publish_term:
        # Consent.objects.create(account=_account, term=_term)
        _term.consent(_account.id, True)

    _account.set_password(data.get('password'))
    _account.last_active = timezone.now()
    _account.save()

    if Config.pull_value('config-verify-email-is-enabled'):
        IdentityVerification.send_verification(_account, 1, 1)  # Send verify email

    Condition.update_all()
    login(request, _account, backend='django.contrib.auth.backends.ModelBackend')
    session_key = request.session.session_key
    if session_key is None:
        request.session.save()
        session_key = request.session.session_key
    Session.push(request.user, session_key)
    request.session.set_expiry(Config.pull_value('config-session-age'))

    if is_web:
        source = 0
    else:
        source = 1

    ip = get_client_ip(request)
    AnalyticSession.push(_account, session_key, source, ip)
    Log.push(request, 'ACCOUNT_REGISTER', 'CONICLE', _account, 'Register Successful', status.HTTP_201_CREATED)

    # For check `is_editable` register profile
    register_profile = Register()
    register_profile.initial_register_profile()
    return AccountSerializer(_account).data, status.HTTP_201_CREATED


class RegisterView(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Account.objects.all()
    allow_redirects = True
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        if not Config.pull_value('config-is-enable-register'):
            raise NotAcceptable
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer_data = serializer.data
        custom_data = {k: request.data[k] for k in set(request.data) - set(serializer.data)}
        data = {**serializer_data, **custom_data}
        response_data, status_response = register(request, data, False)
        return Response(data=response_data, status=status_response)

    def list(self, request, *args, **kwargs):
        if not Config.pull_value('config-is-enable-register'):
            raise NotAcceptable
        register_form = Register()
        return Response(register_form.get_register_form_client)

import logging

from django.contrib.auth import authenticate, login
from django.utils import timezone
from rest_framework import status

from account.models import Account, Session, OneTimePassword
from account.serializers import AccountSerializer
# from config.models import Config
from log.models import Log
# from analytic.models import Session2 as AnalyticSession
from utils.ip import get_client_ip
from account.caches import cached_account_profile
# from group.models import Account as GroupAccount


def login_main(request, data, code, is_web, group='ACCOUNT_LOGIN'):
    logger = logging.getLogger('LOGIN')
    if data['password'] is None:
        Log.push(request, group, code, None,
                 'Hacking!! password is None', status.HTTP_401_UNAUTHORIZED)
        logger.info('401 Unauthorized (%s) Password not entered' % data['username'])
        return {'detail': 'error_email_pass_fail'}, status.HTTP_401_UNAUTHORIZED
    if data['password'].startswith('otp-'):
        if OneTimePassword.is_validate(data['username'], data['password']):
            account = authenticate(username=None, password=None, account_id=data['username'])
            if account is not None:
                account.language = data['language']
                login(request, account)
                # account.last_active = timezone.now()
                # account.save()
                session_key = request.session.session_key
                if session_key is None:
                    request.session.save()
                    session_key = request.session.session_key
                Session.push(request.user, session_key)

                if data['is_remember']:
                    # request.session.set_expiry(Config.pull_value('config-session-age'))
                    # It's sec -> 60*60*24*365 -> ~ 1 Year
                    request.session.set_expiry(31536000)
                else:
                    request.session.set_expiry(0)

                if is_web:
                    source = 0
                else:
                    source = 1
                ip = get_client_ip(request)
                # AnalyticSession.push(account, session_key, source, ip)
                Log.push(request, group, code, account, 'Login success by OTP (%s)' % data['username'], status.HTTP_200_OK)
                return cached_account_profile(account.id), status.HTTP_200_OK
            else:
                Log.push(request, group, code, None, 'Username or Password incorrect (%s)' % data['username'], status.HTTP_401_UNAUTHORIZED, payload={'username': data['username']})
    account = authenticate(username=data['username'].strip().lower(), password=data['password'])
    if account is None:
        formatted_username = data['username'].strip().lower()
        account_by_username = Account.objects.filter(username=formatted_username)
        account_by_email = Account.objects.filter(email=formatted_username).exclude(email__isnull=True)
        _account = account_by_username.first() or account_by_email.first()
        # case: maximum attempt
        if _account and _account.check_login_attempted():
            return {'detail': 'error_maximum_attempt'}, status.HTTP_412_PRECONDITION_FAILED
        # case: not active
        # - account found by username
        # - password match
        # - not active
        if _account and _account.check_password(data['password']) and not _account.is_active:
            Log.push(request, group, code, _account, 'User is inactive', status.HTTP_406_NOT_ACCEPTABLE)
            logger.info('406 Not Acceptable (%s) User is inactive' % data['username'])
            return {'detail': 'error_account_inactive'}, status.HTTP_406_NOT_ACCEPTABLE
        if _account:
            Log.push(request, group, code, _account, 'Password incorrect', status.HTTP_401_UNAUTHORIZED)
            logger.info('401 Unauthorized (%s) Password Incorrect' % data['username'])
        else:
            Log.push(request, group, code, None,
                     'Username incorrect', status.HTTP_401_UNAUTHORIZED, payload={'username': data['username']})
            logger.info('401 Unauthorized (%s) Username Incorrect' % data['username'])
        return {'detail': 'error_email_pass_fail'}, status.HTTP_401_UNAUTHORIZED

    if account.check_login_attempted():
        logger.info('412 Precondition Failed (%s) Maximum Attempt' % data['username'])
        return {'detail': 'error_maximum_attempt'}, status.HTTP_412_PRECONDITION_FAILED

    if not account.is_active:
        Log.push(request, group, code, account, 'User is inactive',
                 status.HTTP_406_NOT_ACCEPTABLE)
        logger.info('406 Not Acceptable (%s) User is inactive' % data['username'])
        return {'detail': 'error_account_inactive'}, status.HTTP_406_NOT_ACCEPTABLE

    if account.check_prolonged_active():
        logger.info('409 Conflict (%s) Prolonged Inactivity' % data['username'])
        return {'detail': 'error_prolonged_inactivity'}, status.HTTP_409_CONFLICT

    if account.is_force_reset_password:
        _data = account.get_token_reset_password(method=2, error='error_account_force_reset_password', device='MOBILE_')
        logger.info('423 Locked (%s) Account Force Reset Password' % data['username'])
        return _data, status.HTTP_423_LOCKED

    if account.check_password_expire:
        _data = account.get_token_reset_password(method=2, error='error_account_password_expired', device='MOBILE_')
        logger.info('423 Locked (%s) Account Password Expired' % data['username'])
        return _data, status.HTTP_423_LOCKED

    account.language = data['language']
    login(request, account)
    account.last_active = timezone.now()
    account.save()
    session_key = request.session.session_key
    if session_key is None:
        request.session.save()
        session_key = request.session.session_key
    Session.push(request.user, session_key)
    request.session.set_expiry(31536000)

    if is_web:
        source = 0
    else:
        source = 1
    ip = get_client_ip(request)
    # AnalyticSession.push(account, session_key, source, ip)
    Log.push(request, group, code, account, 'Login success', status.HTTP_200_OK)
    logger.info('200 OK (%s) Login Success' % data['username'])
    return cached_account_profile(account.id), status.HTTP_200_OK

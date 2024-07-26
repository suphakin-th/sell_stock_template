from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.views import APIView

from account.models import Session
from config.models import Config
from log.models import Log
from utils.response import Response
from account.views_oauth_validate import logout_admd
from login_as_management.models import Log as LoginAsLog
from django.utils import timezone


class LogoutView(APIView):

    def post(self, request):
        account_id = request.user.id
        session_key = request.session.session_key
        config_value = int(Config.pull_value('config-login-backend'))
        if config_value == 3:
            Log.push(request, 'ACCOUNT', 'LOGOUT_SAML', None,
                     'Logout SAML success', status.HTTP_200_OK)
            return redirect('/')
        elif config_value == 7:
            partner = int(Config.pull_value('config-login-oauth-grant-code-partner'))
            if partner == 1:
                logout_admd(request=request, account_id=account_id, session_key=session_key)
        else:
            user = request.user if request.user.is_authenticated else None
            Log.push(request, 'ACCOUNT', 'ACCOUNT_LOGOUT', user,
                     'Logout success', status.HTTP_200_OK)
        logout(request)
        LoginAsLog.push_datetime_logout(account_id, session_key, timezone.now())
        Session.remove(account_id, session_key)
        return Response(status=status.HTTP_200_OK)

    def get(self, request):
        account_id = request.user.id
        session_key = request.session.session_key
        config_value = int(Config.pull_value('config-login-backend'))
        if config_value == 7:
            partner = int(Config.pull_value('config-login-oauth-grant-code-partner'))
            if partner == 1:
                logout_admd(request=request, account_id=account_id, session_key=session_key)
        else:
            user = request.user if request.user.is_authenticated else None
            Log.push(request, 'ACCOUNT', 'ACCOUNT_LOGOUT', user,
                     'Logout success', status.HTTP_200_OK)
        logout(request)
        LoginAsLog.push_datetime_logout(account_id, session_key, timezone.now())
        Session.remove(account_id, session_key)
        return Response(status=status.HTTP_200_OK)

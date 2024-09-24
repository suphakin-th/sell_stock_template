import ast
import copy
import datetime
import json

from django.utils import timezone
from django.conf import settings
from rest_framework import mixins
from rest_framework import viewsets, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound

# from config.models import Config
# from content_permission.models import Condition
from log.models import Log
from utils.response import Response
from .caches import cached_account_profile
from .models import Account
from .serializers import AccountSerializer, ProfileUpdateSerializer, UserDetailSerializer, UserUpdateSerializer
# from login_as_management.models import Log as LoginAsLog


class ProfileView(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    action_serializers = {
        'retrieve': UserDetailSerializer,
        'partial_update': UserUpdateSerializer,
    }

    permission_classes_action = {
        'list': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'profile_patch': [IsAuthenticated],
        'retrieve': [IsAuthenticated]
    }

    def get_permissions(self):
        try:
            return [permission() for permission in self.permission_classes_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        if hasattr(self, 'action_serializers'):
            if self.action in self.action_serializers:
                return self.action_serializers[self.action]
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        response = cached_account_profile(request.user.id)
        is_login_as = None
        datetime_login_as_expire = None
        # if Config.pull_value('login-as-is-enabled'):
        #     log = LoginAsLog.objects.filter(login_as_account_id=request.user.id,
        #                                     session_key=request.session.session_key,
        #                                     datetime_logout=None).values('datetime_login').first()
        #     if log and log.get('datetime_login', None):
        #         is_login_as = True
        #         session_expire_minutes = Config.pull_value('login-as-session-minutes')
        #         datetime_login_as_expire = log.get('datetime_login') + datetime.timedelta(minutes=session_expire_minutes)
                
        response.update({
            'is_login_as': is_login_as,
            'datetime_login_as_expire': timezone.localtime(datetime_login_as_expire) if datetime_login_as_expire else None
        })
        return Response(response)

    def profile_patch(self, request, pk=None):
        """
            Update Profile
            ---
            Parameters:
                - first_name: string
                - last_name: string
                - image: string
                - language: string
            Response Message:
                - code: 200
                  message: ok
        """
        account = get_object_or_404(Account, pk=request.user.id)
        serializer = ProfileUpdateSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        account.cache_delete()
        return Response(self.get_serializer(account).data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.id != instance.id:
            raise NotFound
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        account = self.get_object()
        if request.user.id != account.id:
            raise NotFound
        account_old_log = Account.get_log(account)
        serializer = self.get_serializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        change_data = copy.copy(data)

        if 'count_experience_year' in data and 'count_experience_month' in data:
            account.count_experience = (data['count_experience_year'] * 12) + data['count_experience_month']
            account.save(update_fields=['count_experience'])

        if 'date_birth' in data:
            account.date_birth = data['date_birth']
            account.count_age = account.age

        if 'extra' in data:
            if account.extra not in ['', '{}']:
                extra_data = ast.literal_eval(account.extra)
            else:
                extra_data = {}
            extra = data.pop('extra', {})
            for key, value in extra.items():
                extra_data[key] = value
            account.extra = json.dumps(extra_data)
            account.save(update_fields=['extra'])

        account = serializer.save()
        account.update_data()
        account.cache_delete()
        account_new_log = Account.get_log(account)
        # Condition.update_all()
        Log.push(
            None, 'ACCOUNT', 'UPDATE', request.user, 'Update account',
            status.HTTP_200_OK,
            content_type=settings.CONTENT_TYPE('account.account'), content_id=account.id,
            note='account/views_profile.py partial_update()',
            data_old=account_old_log, data_new=account_new_log, data_change=change_data
        )
        return Response(UserDetailSerializer(account).data)

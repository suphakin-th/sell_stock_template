import ast
import uuid

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from utils.response import Response

from stock_template.account.views_login_main import login_main
from .models import Account
from .serializers import LoginSerializer


class LoginView(viewsets.GenericViewSet):
    queryset = Account.objects.all()
    allow_redirects = True
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data, status_response = login_main(request, data, 'WEB', True)
        return Response(data=data, status=status_response)
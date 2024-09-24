from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Account
from .serializers import AccountSerializer


class AccountView(viewsets.GenericViewSet):
    queryset = Account.objects.none()
    serializer_class = AccountSerializer

    permission_classes_action = {
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
    }

    def get_permissions(self):
        try:
            return [permission() for permission in self.permission_classes_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        if self.request.user.is_authenticated():
            return Account.objects.filter(id=self.request.user.id)
        else:
            return self.queryset
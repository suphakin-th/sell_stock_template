from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from utils.advanced_filters.emoji_filter import SearchFilter

from inbox.models import Content
from inbox.serializers import InboxReadSerializer, InboxListSerializer


class InboxView(mixins.ListModelMixin,
                mixins.CreateModelMixin,
                viewsets.GenericViewSet,):

    queryset = Content.objects.all()
    serializer_class = InboxListSerializer
    filter_backends = (OrderingFilter, SearchFilter)

    ordering_fields = ('title', 'id')
    search_fields = ('title', 'id')

    action_serializers = {
        'list': InboxListSerializer,
        'create': InboxReadSerializer,  # Create Read ann mark content is_read = True,
    }

    def get_queryset(self):
        return self.queryset.filter(inbox__status=1, inbox__member__account=self.request.user)

    def get_serializer_class(self):
        if hasattr(self, 'action_serializers'):
            if self.action in self.action_serializers:
                return self.action_serializers[self.action]
        return super().get_serializer_class()

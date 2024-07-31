from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets
from rest_framework.exceptions import NotFound

from utils.content import get_content_type_list
from .serializers import ContentTypeSerializer


class ContentTypeView(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContentTypeSerializer

    def get_queryset(self):
        id_list = [_.id for _ in get_content_type_list()]

        if len(id_list) > 0:
            return ContentType.objects.filter(id__in=id_list).order_by('-id')
        else:
            raise NotFound('ContentType Not Found')

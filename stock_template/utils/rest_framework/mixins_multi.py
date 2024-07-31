from rest_framework import status
from utils.response import Response

from .serializers_multi_destroy import MultiDestroySerializer


class MultiMixin(object):
    serializer_class = MultiDestroySerializer

    def multi_destroy(self, request):
        """
        delete: json
        field: [value list]
        ex.
        {
          "query": {
            id__in: [1, 2],
            is_display: false
          }
        }
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            queryset.filter(**data['query']).delete()
        except:
            pass
        return Response({}, status=status.HTTP_204_NO_CONTENT)

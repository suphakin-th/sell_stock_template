from django.db.models import F
from rest_framework import status
from log.models import Content as ContentLog
from utils.content_type import get_group_code_by_content_type_id
from utils.response import Response
from utils.rest_framework.serializers import ContentSortSerializer


class SortModelMixin(object):
    serializer_class = ContentSortSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_type = None
        self.content = None

    def clear_cache(self):
        pass

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        queryset = self.get_queryset()
        if queryset is None:
            return Response(status=status.HTTP_409_CONFLICT)

        content = queryset.filter(id=data['id']).first()
        if content:
            last = queryset.order_by('sort').last()
            zero_list = queryset.filter(sort=0)
            if zero_list:
                _ = last.sort
                for zero in zero_list:
                    _ += 1
                    zero.sort = _
                    zero.save(update_fields=['sort'])
            new_position = serializer.data.get('position')
            check_point = queryset.filter(sort=new_position).first()
            if check_point is not None:
                # 0 -> x : x>=1
                if content.sort == 0 and new_position > content.sort:
                    queryset.filter(
                        sort__gte=new_position
                    ).update(sort=F('sort') + 1)
                elif 0 < content.sort != new_position > 0:
                    if content.sort < new_position:
                        if new_position > last.sort:
                            new_position = last.sort+1
                        else:
                            queryset.filter(
                                sort__gt=content.sort,
                                sort__lte=new_position
                            ).update(sort=F('sort') - 1)
                    else:
                        queryset.filter(
                            sort__gte=new_position,
                            sort__lt=content.sort
                        ).update(sort=F('sort') + 1)
                else:
                    pass
            content.sort = new_position
            content.save(update_fields=['sort'])
            self.clear_cache()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

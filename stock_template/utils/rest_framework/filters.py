from rest_framework.filters import BaseFilterBackend


class IDListFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        id_list = [int(x) for x in request.query_params.get("id", '').split(',') if x.isnumeric()]
        if len(id_list) > 0:
            queryset = queryset.filter(id__in=id_list)
        return queryset

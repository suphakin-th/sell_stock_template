import six
from django.conf import settings
from django.core.paginator import InvalidPage
from rest_framework import pagination
from rest_framework.exceptions import NotFound
from rest_framework.response import Response  # Do not change!!

class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'next_url': self.get_next_link(),
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'previous_url': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page_size': page_size if page_size is not None else self.page_size,
            'results': data
        })

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return pagination._positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        page_size = getattr(request, 'page_size', None)
        if page_size is None:
            page_size = 24
            setattr(request, 'page_size', page_size)
        return page_size
class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'next_url': self.get_next_link(),
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'previous_url': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page_size': page_size if page_size is not None else self.page_size,
            'results': data
        })

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return pagination._positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        page_size = getattr(request, 'page_size', None)
        if page_size is None:
            page_size = Config.pull_value('config-page-size')
            setattr(request, 'page_size', page_size)
        return page_size


class ReportSurveyResultPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        self.view = view
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        survey_id = self.view.kwargs.get('survey_id')
        summay = {}
        from survey.models import Question
        queryset = Question.objects.filter(section__survey_id=survey_id)
        summay.update({'count_question': queryset.count()})

        for choice in Question.TYPE_CHOICES:
            type_id = choice[0]
            type_name = choice[1]
            count_type = queryset.filter(type=type_id).count()
            item = {"count_type_%s" % type_name: count_type}
            summay.update(item)

        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'next_url': self.get_next_link(),
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'previous_url': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page_size': page_size if page_size is not None else self.page_size,
            'summary': summay,
            'results': data,
        })

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return pagination._positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        return Config.pull_value('config-page-size')


class FwdReportAttendeeDetailPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        self.view = view
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        content_id = self.view.kwargs.get('event_id')
        content_type = settings.CONTENT_TYPE('event.event')

        instance = ProgressContent.objects.filter(content_id=content_id, content_type=content_type).first()

        if instance:
            learner = instance.learner
            complete = instance.complete
            completed = instance.completed

        else:
            learner = 0
            complete = 0
            completed = 0

        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'next_url': self.get_next_link(),
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'previous_url': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page_size': page_size if page_size is not None else self.page_size,
            'learner': learner,
            'complete': complete,
            'completed': completed,
            'results': data,
        })

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return pagination._positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        return Config.pull_value('config-page-size')


class FwdReportTrainerDetailPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        self.view = view
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        content_id = self.view.kwargs.get('event_id')
        content_type = settings.CONTENT_TYPE('event.event')

        instance = ProgressContent.objects.filter(content_id=content_id, content_type=content_type).first()

        if instance:
            data_header = {"learner": instance.learner,
                           "complete": instance.complete,
                           "completed": instance.completed
                           }
        else:
            data_header = {"learner": 0,
                           "complete": 0,
                           "completed": 0
                           }

        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'next_url': self.get_next_link(),
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'previous_url': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page_size': page_size if page_size is not None else self.page_size,
            "count_attendee": data_header,
            'results': data,
        })

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return pagination._positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        return Config.pull_value('config-page-size')

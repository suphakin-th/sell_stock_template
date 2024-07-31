from django.conf.urls import include, url
from rest_framework import routers

from .viewsets import ContentTypeView

router = routers.DefaultRouter()
router.register('content-type', ContentTypeView, basename='util-content-type')

urlpatterns = [
    url(r'^', include(router.urls)),
]

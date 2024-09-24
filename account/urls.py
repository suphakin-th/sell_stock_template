from django.conf import settings
from django.conf.urls import include
from django.urls import re_path as url

from rest_framework.routers import DefaultRouter, Route
from .views_login import LoginView
from .views_logout import LogoutView

from .views_profile import ProfileView
from .views_register import RegisterView


router = DefaultRouter()
router.include_root_view = settings.ROUTER_INCLUDE_ROOT_VIEW
router.routes[0] = Route(
    url=r'^{prefix}{trailing_slash}$',
    mapping={
        'get': 'list',
        'post': 'create',
        'patch': 'profile_patch',
    },
    name='{basename}-list',
    detail=False,
    initkwargs={'suffix': 'List'}
)
router.register(r'login', LoginView)
router.register(r'profile', ProfileView)
router.register(r'register', RegisterView)


urlpatterns = [
    url(r'logout/$', LogoutView.as_view()),
    url(r'^', include(router.urls)),
]

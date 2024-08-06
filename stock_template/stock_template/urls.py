from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve

from rest_framework_swagger.views import get_swagger_view

from django.conf import settings

urlpatterns_api_user = [
    path('api/account/', include('account.urls')),

]

urlpatterns_swagger = [
    path('api/', get_swagger_view(title='API Docs.', patterns=urlpatterns_api_user)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
]


if settings.SWAGGER_SETTINGS['IS_ENABLE']:
    urlpatterns += urlpatterns_swagger
    
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

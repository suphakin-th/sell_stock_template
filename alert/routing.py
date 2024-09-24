from alert import consumer

from django.conf.urls import url

websocket_urlpatterns = [
    url(r'^websocket/alert/import/$', consumer.AlertImportListConsumer),
    url(r'^websocket/alert/import/(?P<module_name>\w+)/$', consumer.AlertImportModuleListConsumer),
]
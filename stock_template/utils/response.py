from rest_framework.response import Response as RestResponse

# # from config.models import Config
# # from dict.models import Dict
# from filter.caches import cache_filter_update_web
from collections.abc import Iterable


class Response(RestResponse):

    def __init__(self, data=None, status=None,
                 template_name=None, headers=None,
                 exception=False, content_type=None):
        super().__init__(data=data, status=status,
                         template_name=template_name, headers=headers,
                         exception=exception, content_type=content_type)
        if isinstance(self.data, dict):
            _datetime_update = Config.pull_datetime_update_web()
            map_dict = {
                'api': 'web',
                'config_datetime_update': _datetime_update,
                'datetime_update': _datetime_update,  # For IOS old version
                'dict_datetime_update': Dict.pull_last_datetime_update(),
                'filter_update': cache_filter_update_web()
            }
            map_dict.update(self.data)
            self.data = map_dict


class ResponseList(RestResponse):

    def __init__(self, data=None, status=None,
                 template_name=None, headers=None,
                 exception=False, content_type=None):
        super().__init__(data=data, status=status,
                         template_name=template_name, headers=headers,
                         exception=exception, content_type=content_type)
        if isinstance(self.data, Iterable):
            _datetime_update = Config.pull_datetime_update_web()
            map_dict = {
                'api': 'web',
                'config_datetime_update': _datetime_update,
                'datetime_update': _datetime_update,  # For IOS old version
                'dict_datetime_update': Dict.pull_last_datetime_update(),
                'filter_update': cache_filter_update_web()
            }
            map_dict.update({'result': self.data})
            self.data = map_dict

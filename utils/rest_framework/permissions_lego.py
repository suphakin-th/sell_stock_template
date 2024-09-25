from config.models import Config


class LegoPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False
        if Config.pull_value('config-is-lego'):
            if request.user.username in Config.pull_value('config-lego-user'):
                return True
            else:
                return False
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True

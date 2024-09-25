from utils.rest_framework.permissions import BasePermissionAction, get_group


class BasePermissionMultipleAction(object):

    def __init__(self, *args, **kwargs):
        self._message = 'You do not have permission to perform this action.'

    @property
    def message(self):
        return self._message

    def set_message(self, message):
        self._message = message

    def set_message_by_view(self, view):
        class_name = self.__class__.__name__
        message = '%s_' % class_name
        for app, model in view.app_models:
            message += '(%s_%s)|' % (app, model)
        message += ': You do not have permission to perform this action.'
        self.set_message(message)


class ViewPermissionMultiple(BasePermissionMultipleAction):

    def has_permission(self, request, view):
        self.set_message_by_view(view)
        request.is_view = False
        request.is_organization = False
        request.is_department = False
        request.is_level = False
        request.is_group = False
        request.is_provider = False
        request.is_instructor = False
        request.is_support = False
        request.is_inspector = False
        request.is_mentor = False
        request.is_manager = False

        if request.user is None or not request.user.is_authenticated:
            return False

        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.view_%s' % (app, model), group=request.AUTH_GROUP):
                request.is_view = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_organization_%s' % (app, model),
                    group=request.AUTH_GROUP
            ) or request.user.has_perm(
                '%s.view_org_%s' % (app, model),
                group=request.AUTH_GROUP
            ):
                request.is_organization = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_department_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_department = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_level_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_level = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_group_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_group = True
                return True
            elif request.PROVIDER and request.user.has_perm(
                    '%s.view_by_provider_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_provider = True
                return True
            elif request.INSTRUCTOR and request.user.has_perm(
                    '%s.view_by_instructor_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_instructor = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_support_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_support = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_inspector_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_inspector = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_mentor_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_mentor = True
                return True
            elif request.user.has_perm(
                    '%s.view_by_manager_%s' % (app, model),
                    group=request.AUTH_GROUP
            ):
                request.is_manager = True
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True


class AddPermissionMultiple(BasePermissionMultipleAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.add_%s' % (app, model), group=request.AUTH_GROUP):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangePermissionMultiple(BasePermissionMultipleAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.change_%s' % (app, model), group=request.AUTH_GROUP):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True


class DeletePermissionMultiple(BasePermissionMultipleAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.delete_%s' % (app, model), group=request.AUTH_GROUP):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True


class ExportPermissionMultiple(BasePermissionMultipleAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.export_%s' % (app, model), group=request.AUTH_GROUP):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True

class ChangePublishPermissionMultiple(BasePermissionMultipleAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        for app, model in view.app_models:
            if request.user.has_perm('%s.change_publish_%s' % (app, model), group=request.AUTH_GROUP):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True

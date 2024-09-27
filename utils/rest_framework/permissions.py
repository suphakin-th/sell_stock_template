import copy

from rest_framework.permissions import BasePermission

from config.models import Config
from department.caches import cached_department_list_by_account
from department.models import Department
from group.caches import cached_user_group_list_by_account
from group.models import Group


class DenyAny(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


def get_group(request):
    if request.IS_API:
        department_id = request.session.get('department_id', None)
        if department_id is None:
            try:
                request.DEPARTMENT = request.DEPARTMENT_LIST[0]
                request.session['department_id'] = request.DEPARTMENT.id
            except:
                request.DEPARTMENT = None
        else:
            request.DEPARTMENT = Department.pull(department_id)
            if request.DEPARTMENT is not None:
                request.session['department_id'] = request.DEPARTMENT.id

                request.DEPARTMENT_LIST = cached_department_list_by_account(request.user.id)
                department_id = request.session.get('department_id', None)
                if department_id is None:
                    try:
                        request.DEPARTMENT = request.DEPARTMENT_LIST[0]
                        request.session['department_id'] = request.DEPARTMENT.id
                    except:
                        request.DEPARTMENT = None
                else:
                    request.DEPARTMENT = Department.pull(department_id)
                    if request.DEPARTMENT is not None:
                        request.session['department_id'] = request.DEPARTMENT.id

        group_id = request.session.get('group_id', None)
        if group_id is None:
            try:
                request.GROUP = request.GROUP_LIST[0]
                request.session['group_id'] = request.GROUP.id
            except:
                request.GROUP = None
        else:
            request.GROUP = Group.pull(group_id)
            if request.GROUP is not None:
                request.session['group_id'] = request.GROUP.id

                request.GROUP_LIST = cached_user_group_list_by_account(request.user.id)
                group_id = request.session.get('group_id', None)
                if group_id is None:
                    try:
                        request.GROUP = request.GROUP_LIST[0]
                        request.session['group_id'] = request.GROUP.id
                    except:
                        request.GROUP = None
                else:
                    request.GROUP = Group.pull(group_id)
                    if request.GROUP is not None:
                        request.session['group_id'] = request.GROUP.id
    else:
        request.AUTH_GROUP_LIST = []
        request.PROVIDER_LIST = []
        request.INSTRUCTOR_LIST = []
        request.DEPARTMENT_LIST = []
        request.GROUP_LIST = []
        request.AUTH_GROUP = None
        request.PROVIDER = None
        request.INSTRUCTOR = None
        request.DEPARTMENT = None
        request.GROUP = None


class BasePermissionAction(object):

    def __init__(self, *args, **kwargs):
        self._message = 'You do not have permission to perform this action.'

    @property
    def message(self):
        return self._message

    def set_message(self, message):
        self._message = message

    def set_message_by_view(self, view):
        class_name = self.__class__.__name__
        app = getattr(view, 'app', '')
        model = getattr(view, 'model', '')
        message = '%s_%s.%s: You do not have permission to perform this action.' % (class_name, app, model)
        self.set_message(message)


class ViewPermission(BasePermissionAction):

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
        request.is_supervisor = False

        if request.user is None or not request.user.is_authenticated:
            return False

        # A = app name
        # P = permission name
        # M = model name (lowercase)
        # A.P_M
        # content_request.view_contentrequest
        get_group(request)
        if request.user.has_perm('%s.view_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            request.is_view = True
            return True
        elif request.user.has_perm(
                '%s.view_by_organization_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ) or request.user.has_perm(
            '%s.view_org_%s' % (view.app, view.model),
            group=request.AUTH_GROUP
        ):
            request.is_organization = True
            return True
        elif request.user.has_perm(
                '%s.view_by_department_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_department = True
            return True
        elif request.user.has_perm(
                '%s.view_by_level_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_level = True
            return True
        elif request.user.has_perm(
                '%s.view_by_group_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_group = True
            return True
        elif request.PROVIDER and request.user.has_perm(
                '%s.view_by_provider_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_provider = True
            return True
        elif request.INSTRUCTOR and request.user.has_perm(
                '%s.view_by_instructor_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_instructor = True
            return True
        elif request.user.has_perm(
                '%s.view_by_support_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_support = True
            return True
        elif request.user.has_perm(
                '%s.view_by_inspector_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_inspector = True
            return True
        elif request.user.has_perm(
                '%s.view_by_mentor_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_mentor = True
            return True
        elif request.user.has_perm(
                '%s.view_by_manager_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_manager = True
            return True
        elif request.user.has_perm(
                '%s.view_by_supervisor_%s' % (view.app, view.model),
                group=request.AUTH_GROUP
        ):
            request.is_supervisor = True
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewContentPermission(ViewPermission):
    """for override app and model to content.content"""

    def has_permission(self, request, view):
        _view = copy.copy(view)
        _view.app = 'content'
        _view.model = 'content'
        result = super().has_permission(request, _view)
        return result


class IsSuperAdmin(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user.is_superuser)


class ViewContentCheckinPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_content_check_in_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewTokenPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        get_group(request)
        if request.user.has_perm('%s.view_token_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class AddPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.add_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


# class ApproveContentPermission(object):
#     def has_permission(self, request, view):
#         if request.user is None or not request.user.is_authenticated:
#             return False
#         get_group(request)
#         if request.user.has_perm('%s.approve_content_%s' % (view.app, view.model), group=request.AUTH_GROUP):
#             return True
#         else:
#             return False
#
#     def has_object_permission(self, request, view, obj):
#         return True


class ChangePermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeProgressPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_progress_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangePublishPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_publish_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeCertificatePermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_certificate_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeTransactionPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_transaction_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeAccountPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_account_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeContentCheckinPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_content_check_in_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class CancelContentPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.cancel_content_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class DeletePermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.delete_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class CancelRequestPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.cancel_request_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewFormPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_form_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ExportPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.export_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True

class UnauthorizedPermission(object):
    def has_permission(self, request, view):
        from django.conf import settings
        if request.user.is_authenticated or settings.IS_EXPLORE:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        return True


# ref: ClickUp - 7hyzrr
class DeleteMaterialPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.delete_material_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewLearnerPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_learner_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewProgressPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_progress_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class AddMaterialPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.add_material_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ChangeMaterialPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.change_material_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewApprovePermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_approve_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False


class BaseActionHandleExceptionToNotFound(object):
    def __init__(self, *args, **kwargs):
        self._message = 'You do not have duty to perform this action.'

    @property
    def message(self):
        return self._message

    @property
    def status_code(self):
        from rest_framework.exceptions import NotFound
        raise NotFound

    def set_message(self, message):
        self._message = message

    def set_message_by_view(self, view):
        class_name = self.__class__.__name__
        message = '%s: You do not have duty to perform this action.' % (class_name)
        self.set_message(message)


class LearningPlaylistConfig(BaseActionHandleExceptionToNotFound):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if Config.pull_value('learning-playlist-is-enabled'):
            return True
        else:
            self.status_code
            return False

    def has_object_permission(self, request, view, obj):
        return True


class ViewCustomReportPermission(BasePermissionAction):
    def has_permission(self, request, view):
        self.set_message_by_view(view)
        if request.user is None or not request.user.is_authenticated:
            return False
        get_group(request)
        if request.user.has_perm('%s.view_custom_%s' % ('report', 'report'), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True



class CanLoginAsPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False

        get_group(request)
        if request.user.has_perm('%s.can_login_as_%s' % (view.app, view.model), group=request.AUTH_GROUP):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return True
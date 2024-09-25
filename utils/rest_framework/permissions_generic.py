

from .permissions import ViewPermission, AddPermission, ChangePermission, DeletePermission


class PermissionDashboardGeneric(object):
    permission_classes_action = {
        'list': [ViewPermission],
        'retrieve': [ViewPermission],
        'create': [ViewPermission, AddPermission],
        'update': [ViewPermission, ChangePermission],
        'partial_update': [ViewPermission, ChangePermission],
        'destroy': [ViewPermission, DeletePermission]
    }

    def get_permissions(self):
        try:
            return [permission() for permission in self.permission_classes_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]

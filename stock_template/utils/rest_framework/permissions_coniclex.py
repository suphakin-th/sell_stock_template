class ConicleXPermission(object):
    def has_permission(self, request, view):
        if request.user is None or not request.user.is_authenticated:
            return False

        for group in request.AUTH_GROUP_LIST:
            if group.id == 17:
                return True
        return False

    def has_object_permission(self, request, view, obj):
        return True

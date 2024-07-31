from rest_framework import serializers


class ValidationWhileSpace(object):

    @staticmethod
    def update_validate(serializers_obj, data, allow_field_list=None):

        # allow whileSpace list.
        if allow_field_list is None:
            allow_field_list = []

        for allow_field in allow_field_list:
            if allow_field in data:
                name = data.get(allow_field, '')
                if name.isspace():
                    serializers_obj.fields[allow_field].trim_whitespace = False

        return serializers_obj

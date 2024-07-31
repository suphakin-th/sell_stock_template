import base64
import binascii
import mimetypes
import uuid
import django


from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.fields import Field, SkipField, empty
from rest_framework.serializers import IntegerField, Serializer
from django.utils.translation import gettext
django.utils.translation.ugettext = gettext
from django.utils.translation import ugettext as _



class ContentTypeSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()

    class Meta:
        model = ContentType
        fields = (
            'id',
            'code',
        )

    @staticmethod
    def get_code(content_type):
        return '%s.%s' % (content_type.app_label, content_type.model)

class ContentTypeDictSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_id(self, value):
        return value['content_type'].id

    def get_type(self, value):
        return value.get('type', None)

    def to_representation(self, value):
        res = super().to_representation(value)

        model = value['content_type'].model
        code = '%s.%s' % (value['content_type'].app_label, value['content_type'].model)

        res.update({
            'code': code,
            'group': 'external' if model in ['coniclex', 'articleconiclex', 'pdfconiclex'] else 'internal'
        })

        return res


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-restframework-framework/pull/1268

    Updated for Django REST framework 3.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if 'data:' in data and ';base64,' in data:
                # Break out the header from the base64 content
                header, data = data.split(';base64,')

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except:
                self.fail('invalid_image')

            # Generate file name:
            file_name = str(uuid.uuid4())[:12]  # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension,)

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr
        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension
        if extension is None:
            extension = 'jpg'
        return extension

    def validate_empty_values(self, data):
        if data is empty:
            if getattr(self.root, 'partial', False):
                raise SkipField()

        if self.allow_empty_file and isinstance(data, str) and len(data) == 0:
            return True, None

        if self.allow_empty_file and data is empty:
            return True, None
        elif self.allow_null and data is None:
            return True, None
        else:
            return False, data


class Base64FileField(Field):
    # mimetypes.guess_extension() may return different values for same mimetype, but we need one extension for one mime
    _MIME_MAPPING = {
        'image/jpeg': '.jpg',
        'audio/wav': '.wav'
    }
    _ERROR_MESSAGE = _('Base64 string is incorrect')

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(self._ERROR_MESSAGE)
        try:
            mime, encoded_data = data.replace('data:', '', 1).split(';base64,')
            extension = self._MIME_MAPPING[mime] if mime in self._MIME_MAPPING.keys() else mimetypes.guess_extension(
                mime)
            file = ContentFile(base64.b64decode(encoded_data), name='{name}{extension}'.format(name=str(uuid.uuid4()),
                                                                                               extension=extension))
        except (ValueError, binascii.Error):
            raise serializers.ValidationError(self._ERROR_MESSAGE)
        return file

    def to_representation(self, value):
        if not value:
            return None
        return value.url


class ContentSortSerializer(Serializer):
    id = IntegerField()
    position = IntegerField()

    def validate_position(self, value):
        if value < 1:
            return 1
        else:
            return value


class NoneSerializer(serializers.Serializer):
    pass


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass!
        allowed_fields = kwargs.pop('fields', None)
        excluded_fields = kwargs.pop('exclude_fields', None)
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if allowed_fields is not None and excluded_fields is not None:
            # Drop any fields that are specified and not specified in the `fields` argument.
            allowed = set(allowed_fields)
            excluded = set(excluded_fields)
            existing = set(self.fields)

            for field_name in (existing - allowed).union(existing - (existing - excluded)):
                self.fields.pop(field_name)
        else:
            if allowed_fields is not None:
                # Drop any fields that are not specified in the `fields` argument.
                allowed = set(allowed_fields)
                existing = set(self.fields)
                for field_name in existing - allowed:
                    self.fields.pop(field_name)

            if excluded_fields is not None:
                # Drop any fields that are specified in the `fields` argument.
                excluded = set(excluded_fields)
                existing = set(self.fields)
                for field_name in existing - (existing - excluded):
                    self.fields.pop(field_name)

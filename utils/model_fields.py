import json

from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class JSONField(models.TextField):
    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, str):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def from_db_value(self, value, *args):
        return self.to_python(value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        elif isinstance(value, dict):
            return json.dumps(value)
        else:
            return value

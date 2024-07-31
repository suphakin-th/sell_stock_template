from rest_framework import serializers


class MultiDestroySerializer(serializers.Serializer):
    query = serializers.JSONField()

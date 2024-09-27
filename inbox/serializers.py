from django.db import models
from rest_framework import serializers
from inbox.models import Content, Inbox
from news_update.models import NewsUpdate
from utils.content import get_content, get_code


class InboxReadSerializer(serializers.Serializer):
    id_list = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    channel = serializers.IntegerField(min_value=1, max_value=3, default=3)

    def save(self, **kwargs):
        validated_data = dict(
            list(self.validated_data.items()) + list(kwargs.items())
        )
        return self.create(validated_data)

    def create(self, validated_data):
        id_list = validated_data.get('id_list')
        channel = validated_data.get('channel')

        inbox_list = Inbox.objects.filter(id__in=id_list, status=1)

        request = self.context.get('request')
        account = request.user
        for inbox in inbox_list:
            if not inbox.read_set.filter(account=account, channel=channel).exists():
                inbox.read_set.create(account=account, channel=channel)
        return inbox_list


class ContentSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    datetime_create = serializers.SerializerMethodField()

    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    content_type_id = serializers.SerializerMethodField()
    content_type_name = serializers.SerializerMethodField()
    content_name = serializers.SerializerMethodField()
    content_image = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = ('id',
                  'body',
                  'title',
                  'type',
                  'type_display',
                  'datetime_create',

                  'name',
                  'email',
                  'image',

                  'content_type_id',
                  'content_type_name',
                  'content_id',
                  'content_name',
                  'content_image',)

    def get_id(self, content):
        return content.inbox.id

    def get_body(self, content):
        return content.get_body()

    def get_title(self, content):
        return content.inbox.title

    def get_type(self, content):
        return content.inbox.type

    def get_type_display(self, content):
        return content.inbox.get_type_display()

    def get_datetime_create(self, content):
        return content.inbox.datetime_create

    def get_name(self, content):
        account = content.inbox.account
        if account is None:
            return "-"
        else:
            return account.get_full_name()

    def get_email(self, content):
        account = content.inbox.account
        if account is None:
            return "-"
        else:
            return account.email

    def get_image(self, content):
        account = content.inbox.account
        if account is None:
            return "-"
        else:
            if not account.image:
                return "-"
            else:
                return account.image.url

    def get_content_type_id(self, content):
        return content.content_type_id

    def get_content_type_name(self, content):
        return content.content_type.app_label

    def get_content_name(self, content):
        obj = content.content
        if obj is None:
            return "-"
        else:
            name = getattr(obj, "name", "-")
            return name

    def get_content_image(self, content):
        obj = content.content
        if obj is None:
            return "-"
        else:
            if hasattr(obj, "image"):
                image = getattr(obj, "image", "-")
                return image
            else:
                return "-"


class InboxContentSerilailizer(serializers.ModelSerializer):
    # Inbox
    type_display = serializers.SerializerMethodField()

    # Account
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    # Set Cotent Empty
    content_type_id = serializers.IntegerField(default=0, allow_null=True)
    content_type_name = serializers.CharField(default="-", allow_null=True, allow_blank=True)
    content_id = serializers.IntegerField(default=0, allow_null=True)
    content_name = serializers.CharField(default="-", allow_null=True, allow_blank=True)
    content_image = serializers.CharField(default="-", allow_null=True, allow_blank=True)

    class Meta:
        model = Inbox
        fields = (
            'id',
            'body',
            'title',
            'type',
            'type_display',
            'datetime_create',

            'name',
            'email',
            'image',

            'content_type_id',
            'content_type_name',
            'content_id',
            'content_name',
            'content_image'
        )

    def get_type_display(self, inbox):
        return inbox.get_type_display()

    def get_name(self, inbox):
        if inbox.account is None:
            return "-"
        else:
            return inbox.account.get_full_name()

    def get_email(self, inbox):
        if inbox.account is None:
            return "-"
        else:
            return inbox.account.email

    def get_image(self, inbox):
        if getattr():
            return "-"
        else:
            account = inbox.account
            if not account.image:
                return "-"
            else:
                return account.image.url


class InboxContentListSerializer(serializers.ListSerializer):

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        iterable = data.all() if isinstance(data, models.Manager) else data
        qureryset = Inbox.objects.filter(content__isnull=True)
        inbox_list = InboxContentSerilailizer(instance=qureryset, many=True).data
        content_list = ContentSerializer(instance=iterable, many=True).data
        return inbox_list + content_list


class InboxListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ('content_id',)
        extra_kwargs = {'content_id': {'write_only': True}}
        list_serializer_class = InboxContentListSerializer


class DirecMessageSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Inbox
        fields = ('title', 'body')


class FCMContenSerializer(serializers.ModelSerializer):
    content_type_name = serializers.SerializerMethodField()
    content_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = ('content_id',
                  'content_type',
                  'content_type_name',
                  'content_name',
                  'image',
                  'code')

    def get_content_type_name(self, inbox_content):
        return inbox_content.content_type.name

    def get_content_name(self, inbox_content):
        content = get_content(inbox_content.content_type_id, inbox_content.content_id)
        if content:
            return content.name
        else:
            return '-'

    def get_image(self, inbox_content):
        content = get_content(inbox_content.content_type_id, inbox_content.content_id)
        image = getattr(content, 'image', None)
        if image:
            if not image.url:
                return ''
            else:
                return image.url
        else:
            return ''

    def get_code(self, inbox_content):
        return get_code(inbox_content.content_type)


class FCMInboxSerializer(serializers.ModelSerializer):
    content_type_name = serializers.SerializerMethodField()
    content_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()

    class Meta:
        model = Inbox
        fields = ('content_id',
                  'content_type',
                  'content_type_name',
                  'content_name',
                  'image',
                  'code')

    def get_content_type_name(self, inbox):
        from django.conf import settings

        if inbox.type == 2:

            return settings.CONTENT_TYPE('news_update.newsupdate').name
        else:
            return settings.CONTENT_TYPE('inbox.inbox').name

    def get_content_name(self, inbox):
        if inbox.type == 2:
            news = NewsUpdate.objects.filter(id=inbox.content_id).first()
            if news:
                return getattr(news, 'name', '')
            else:
                return ''
        elif inbox.type == 1:
            return inbox.title
        else:
            return ''

    def get_image(self, inbox):
        if inbox.type == 2:
            news_update = NewsUpdate.objects.get(id=inbox.content_id)
            if news_update:
                gallery = news_update.gallery_set.filter(is_cover=True).first()
                if gallery:
                    if not gallery.image:
                        return ''
                    else:
                        return gallery.image.url
                else:
                    return ''
        elif inbox.type == 1:
            if not inbox.image:
                return ''
            else:
                return inbox.image.url
        else:
            return ''

    def get_code(self, inbox):
        from django.conf import settings
        if inbox.type == 2:
            return get_code(settings.CONTENT_TYPE('news_update.newsupdate'))
        else:
            return get_code(settings.CONTENT_TYPE('inbox.inbox'))

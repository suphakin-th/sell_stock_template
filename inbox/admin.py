from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from account.models import Account
from .models import Inbox, Member, Count, Content, Read


@admin.register(Inbox)
class Inbox(admin.ModelAdmin):
    list_display = ('id', 'account', 'type', 'content_type', 'datetime_send', 'datetime_create')
    actions = ['notification_fcm', 'notification_email', 'notification']
    search_fields = ['account__email']
    readonly_fields = ['account', 'content_type']

    def notification_fcm(self, request, queryset):
        for inbox in queryset:
            inbox.send_notification_fcm()

    def notification_email(self, request, queryset):
        for inbox in queryset:
            inbox.send_notification_email()

    def notification(self, request, queryset):
        for inbox in queryset:
            inbox.send_notification()


admin.site.register(Read)


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'inbox', 'content_id', 'content_type', 'content', 'datetime_create')
    search_fields = ['content_type__app_label', 'inbox__id']
    ordering = ['inbox', 'content_type__app_label', 'content_id']

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'inbox', 'datetime_create')
    search_fields = ('account__first_name', 'account__last_name', 'account__code', 'account__code2', 'account__email',
                     'account__username')
    ordering = ('-inbox__datetime_create',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'account':
            kwargs["queryset"] = Account.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Count)
class CountAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'count')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'account':
            kwargs["queryset"] = Account.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def reset_zero(self, request, queryset):
        for count in queryset:
            count.count = 0
            count.save()

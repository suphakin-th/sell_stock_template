from django.contrib import admin

from account.models import Account, Forgot, Session, PasswordHistory, Token, QrCode, SSOToken, OneTimePassword, Avatar
from account.models import IdentityVerification


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'external_id',
        'code',
        'username',
        'email',
        'title',
        'first_name',
        'last_name',
        'gender',
        'datetime_update',
        'type',
        'is_force_reset_password',
        'is_active',

    )

    readonly_fields = ('user_permissions',)
    actions = ['set_type_to_system_user', 'update']
    search_fields = ['external_id', 'code', 'username', 'email', 'first_name', 'last_name']

    @staticmethod
    def set_type_to_system_user(self, request, queryset):
        queryset.update(type=1)

    @staticmethod
    def update(self, request, queryset):
        for account in queryset:
            account.update_data()


@admin.register(Forgot)
class Forgot(admin.ModelAdmin):
    list_display = ('id', 'account', 'token', 'status', 'method', 'datetime_create')
    ordering = ('-datetime_create',)
    search_fields = ('account__username', 'account__email',)
    list_filter = ('method',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('account', 'session_key', 'datetime_create')
    search_fields = ('account__email', 'session_key')


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ('account', 'password', 'datetime_create')
    search_fields = ('account__first_name', 'account__last_name', 'account__code', 'account__code2', 'account__email',
                     'account__username')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('account', 'token', 'datetime_create')
    search_fields = ('account__username', 'account__first_name', 'account__last_name', 'token')


# admin.site.register(QrCode)


@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'status')
    search_fields = ('account__username', 'status')


@admin.register(SSOToken)
class SSOTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'is_active')
    search_fields = ('account__username', 'status')


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'token',
        'account',
        'status',
        'method',
        'send_method',
        'datetime_create',
        'datetime_expire',
    )
    search_fields = ('account__username', 'account__email', 'account__first_name', 'token')


@admin.register(OneTimePassword)
class OneTimePasswordAdmin(admin.ModelAdmin):
    list_display = (
        'otp_code',
        'account',
        'status',
        'datetime_create',
        'datetime_expire',
    )
    search_fields = ('account__username', 'account__email', 'account__first_name', 'otp_code')


@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'image',
        'sort',
        'datetime_create',
    )

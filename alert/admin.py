from django.contrib import admin

from alert.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'code', 'progress', 'duration', 'is_force', 'status', 'datetime_create')
    readonly_fields = ('account', 'datetime_create', 'datetime_update')
    search_fields = ['code', ]

    def progress(self, alert):
        return '%s/%s' % (
            alert.count_row_complete,
            alert.count_row
        )

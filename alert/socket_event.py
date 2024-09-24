from alert.dashboard.serializers_import_history import AlertImportHistoryEventSerializer
from alert.models import Alert


async def import_history_processing_list(obj):
    alert_processing_list = Alert.objects.filter(action_type=2, status__in=[0, 1, 2], account__id=obj.user.id,
                                                 module_name=obj.module_name)
    import_history_data = {
        'event': 'import_history_processing_list',
        'data': AlertImportHistoryEventSerializer(alert_processing_list, many=True).data
    }
    await obj.channel_layer.group_send(obj.individual_group_name, {'type': 'send_event', 'data': import_history_data})

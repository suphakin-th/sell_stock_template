from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from alert.socket_event import import_history_processing_list


class AlertImportListConsumer(AsyncJsonWebsocketConsumer):
    user = None
    session_id = None
    content_type_id = -1
    content_id = -1

    broadcast_group_name = ''
    individual_group_name = ''

    async def connect(self):
        if self.scope["user"].is_anonymous:
            self.disconnect()
        self.user = self.scope["user"]
        self.session_id = self.scope['cookies']['sessionid']
        self.broadcast_group_name = "import_history"
        await self.channel_layer.group_add(self.broadcast_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.broadcast_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        event_type = text_data_json['event']
        data = text_data_json['data']

    async def send_event(self, event):
        await self.send_json(
            {
                'event': event['data']['event'],
                'data': event['data']['data']
            }
        )


class AlertImportModuleListConsumer(AsyncJsonWebsocketConsumer):
    user = None
    session_id = None
    content_type_id = -1
    content_id = -1

    individual_group_name = ''
    module_name = ''

    async def connect(self):
        if self.scope["user"].is_anonymous:
            self.disconnect()
        self.user = self.scope["user"]
        self.session_id = self.scope['cookies']['sessionid']
        try:
            module, function = self.scope['url_route']['kwargs']['module_name'].split('__')
            self.module_name = '%s (%s)' % (module.replace('_', ' '), function.replace('_', ' '))
        except:
            self.module_name = self.scope['url_route']['kwargs']['module_name'].replace('_', ' ')
        self.individual_group_name = 'import_history_%s_%s' % (self.user.id, self.scope['url_route']['kwargs']['module_name'].lower())
        await self.channel_layer.group_add(self.individual_group_name, self.channel_name)
        await self.accept()

        await import_history_processing_list(self)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.individual_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        event_type = text_data_json['event']
        data = text_data_json['data']

    async def send_event(self, event):
        await self.send_json({'event': event['data']['event'], 'data': event['data']['data']})

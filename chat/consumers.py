import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
from .models import DirectMessage, GroupMessage, DirectChat, Group

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f"WebSocket connected for user {self.user.username} to room {self.room_group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected for user {self.user.username} from room {self.room_group_name}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message')
        room_type = text_data_json.get('type', 'group')
        
        # Check if this is just a 'broadcast' request (message already saved via API)
        # The frontend should send { "type": "broadcast", "message_id": 123 }
        # OR standard message { "message": "hello" }
        msg_type = text_data_json.get('msg_type', 'new_message')

        if not message_text and msg_type == 'new_message':
            return

        # Scenario 1: Message already saved via REST API, just broadcasting
        if msg_type == 'broadcast' and 'message_data' in text_data_json:
            message_data = text_data_json['message_data']
            print(f"Broadcasting existing message: {message_data['id']}")
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
            return

        # Scenario 2: Message sent via WebSocket directly (needs saving)
        message_data = await self.save_message(message_text, room_type)
        
        if not message_data:
            return

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @database_sync_to_async
    def save_message(self, message_text, room_type):
        try:
            room_id = int(self.room_name)
            
            if room_type == 'group':
                group = Group.objects.get(id=room_id)
                message = GroupMessage.objects.create(
                    group=group,
                    sender=self.user,
                    message_text=message_text
                )
                return {
                    'id': message.id,
                    'sender': {
                        'id': self.user.id,
                        'username': self.user.username,
                    },
                    'content': message.message_text,
                    'timestamp': message.created_at.isoformat(),
                }
                
            elif room_type == 'dm':
                chat = DirectChat.objects.get(id=room_id)
                message = DirectMessage.objects.create(
                    chat=chat,
                    sender=self.user,
                    message_text=message_text
                )
                return {
                    'id': message.id,
                    'sender': {
                        'id': self.user.id,
                        'username': self.user.username,
                    },
                    'content': message.message_text,
                    'timestamp': message.created_at.isoformat(),
                }
                
        except (Group.DoesNotExist, DirectChat.DoesNotExist, ValueError) as e:
            print(f"Error saving message: {e}")
            return None
        return None

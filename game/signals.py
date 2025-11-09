from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GameEvent, ChatMessage, Player, GameRoom

@receiver(post_save, sender=GameEvent)
def broadcast_game_event(sender, instance, created, **kwargs):
    """Отправляет событие игры всем участникам комнаты через WebSocket"""
    if created:
        channel_layer = get_channel_layer()
        room_group_name = f'game_{instance.session.room.room_id}'
        
        # Формируем данные события в зависимости от типа
        event_data = {
            'type': instance.type,
            'player': {
                'id': instance.player.id,
                'username': instance.player.user.username
            } if instance.player else None,
            'target_player': {
                'id': instance.target_player.id,
                'username': instance.target_player.user.username
            } if instance.target_player else None,
            'data': instance.data,
            'timestamp': instance.timestamp.isoformat()
        }
        
        # Отправляем событие в группу комнаты
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'game_event',
                'event': event_data
            }
        )

@receiver(post_save, sender=ChatMessage)
def broadcast_chat_message(sender, instance, created, **kwargs):
    """Отправляет сообщение чата всем участникам комнаты через WebSocket"""
    if created:
        channel_layer = get_channel_layer()
        room_group_name = f'game_{instance.room.room_id}'
        
        # Отправляем сообщение в группу комнаты
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': instance.message,
                'user_id': instance.user.id,
                'username': instance.user.username,
                'timestamp': instance.timestamp.isoformat()
            }
        )

@receiver(post_save, sender=Player)
def broadcast_player_update(sender, instance, created, **kwargs):
    """Отправляет обновление статуса игрока всем участникам комнаты через WebSocket"""
    if not created:  # Только при обновлении, не при создании
        channel_layer = get_channel_layer()
        room_group_name = f'game_{instance.room.room_id}'
        
        # Отправляем обновление в группу комнаты
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'player_status',
                'player_id': instance.user_id,
                'status': instance.status,
                'user_id': instance.user.id,
                'username': instance.user.username
            }
        )

@receiver(post_save, sender=GameRoom)
def broadcast_room_update(sender, instance, created, **kwargs):
    """Отправляет обновление статуса комнаты всем участникам через WebSocket"""
    if not created:  # Только при обновлении, не при создании
        channel_layer = get_channel_layer()
        room_group_name = f'game_{instance.room_id}'
        
        # Отправляем обновление в группу комнаты
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'room_status',
                'room_id': instance.room_id,
                'status': instance.status
            }
        )

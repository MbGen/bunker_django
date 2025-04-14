import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import GameRoom, Player, ChatMessage, GameEvent, GameSession

class GameConsumer(AsyncWebsocketConsumer):
    """WebSocket потребитель для игровой комнаты"""
    
    async def connect(self):
        """Подключение к WebSocket"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'game_{self.room_id}'
        self.user = self.scope['user']
        
        # Проверяем, есть ли пользователь в комнате
        if not await self.is_user_in_room():
            await self.close()
            return
        
        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем сообщение о подключении
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_connect',
                'user_id': self.user.id,
                'username': self.user.username,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def disconnect(self, close_code):
        """Отключение от WebSocket"""
        # Покидаем группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Отправляем сообщение об отключении
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_disconnect',
                'user_id': self.user.id,
                'username': self.user.username,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def receive(self, text_data):
        """Получение сообщения от клиента"""
        data = json.loads(text_data)
        print("WE RECEIVE FROM FRONTEND: ", data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            # Обрабатываем сообщение чата
            await self.handle_chat_message(data)
        elif message_type == 'player_ready':
            # Обрабатываем статус готовности игрока
            await self.handle_player_ready(data)
        elif message_type == 'reveal_attribute':
            # Обрабатываем раскрытие атрибута
            await self.handle_reveal_attribute(data)
        elif message_type == 'vote':
            # Обрабатываем голосование
            await self.handle_vote(data)
        elif message_type == 'use_card':
            # Обрабатываем использование карты
            await self.handle_use_card(data)
        elif message_type == 'next_player':
            # Обрабатываем переход хода
            await self.handle_next_player(data)
    
    async def handle_chat_message(self, data):
        """Обработка сообщения чата"""
        message = data.get('message', '').strip()
        
        if not message:
            return
        
        # Сохраняем сообщение в базе данных
        chat_message = await self.save_chat_message(message)
        
        # Отправляем сообщение всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': self.user.id,
                'username': self.user.username,
                'timestamp': chat_message.timestamp.isoformat()
            }
        )
    
    async def handle_player_ready(self, data):
        """Обработка статуса готовности игрока"""
        player_id = data.get('player_id')
        ready = data.get('ready', True)
        
        # Проверяем, принадлежит ли игрок текущему пользователю
        if not await self.is_player_owner(player_id):
            return
        
        # Обновляем статус готовности
        success, message = await self.update_player_ready(player_id, ready)
        
        if success:
            # Отправляем обновление всем в группе
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_status',
                    'player_id': player_id,
                    'status': 'ready' if ready else 'waiting',
                    'user_id': self.user.id,
                    'username': self.user.username
                }
            )
    
    async def handle_reveal_attribute(self, data):
        """Обработка раскрытия атрибута"""
        player_id = data.get('player_id')
        attribute = data.get('attribute')
        
        # Проверяем, принадлежит ли игрок текущему пользователю
        if not await self.is_player_owner(player_id):
            return
        
        # Раскрываем атрибут
        success, message, value = await self.reveal_player_attribute(player_id, attribute)
        
        if success:
            # Отправляем обновление всем в группе
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'attribute_revealed',
                    'player_id': player_id,
                    'attribute': attribute,
                    'value': value,
                    'user_id': self.user.id,
                    'username': self.user.username
                }
            )
    
    async def handle_vote(self, data):
        """Обработка голосования"""
        session_id = data.get('session_id')
        voter_id = data.get('voter_id')
        target_id = data.get('target_id')
        
        # Проверяем, принадлежит ли голосующий текущему пользователю
        if not await self.is_player_owner(voter_id):
            return
        
        # Голосуем
        success, message, elimination_data = await self.vote_for_player(session_id, voter_id, target_id)
        
        # Отправляем обновление всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'vote_cast',
                'voter_id': voter_id,
                'target_id': target_id,
                'success': success,
                'message': message,
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
        
        # Если произошло исключение игрока или переход к новому раунду
        if success and elimination_data:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_eliminated' if elimination_data.get('eliminated') else 'new_round',
                    'data': elimination_data,
                    'message': message
                }
            )
    
    async def handle_use_card(self, data):
        """Обработка использования карты"""
        card_id = data.get('card_id')
        player_id = data.get('player_id')
        target_id = data.get('target_id')
        additional_data = data.get('additional_data', {})
        
        # Проверяем, принадлежит ли игрок текущему пользователю
        if not await self.is_player_owner(player_id):
            return
        
        # Используем карту
        success, message, effect_data = await self.use_player_card(card_id, player_id, target_id, additional_data)
        
        # Отправляем обновление всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'card_used',
                'player_id': player_id,
                'card_id': card_id,
                'target_id': target_id,
                'success': success,
                'message': message,
                'effect_data': effect_data,
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def handle_next_player(self, data):
        """Обработка перехода хода"""
        session_id = data.get('session_id')
        
        # Получаем следующего игрока
        player, message = await self.get_next_player(session_id)
        print("NEXT PLAYER", player) 
        if player:
            # Отправляем обновление всем в группе
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'next_player',
                    'player_id': player['id'],
                    'username': player['username'],
                    'message': message
                }
            )
    
    async def handle_game_start(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_start',
                'message': 'Игра началась!'
            }
        )

    # Обработчики сообщений от группы
    async def game_event(self, event):
        print("GAME EVENT HANDLER", event)

    async def room_status(self, event):
        print("ROOM STATUS EVENT HANDLER", event)
        await self.send(text_data=json.dumps(event))

    async def user_connect(self, event):
        """Отправка сообщения о подключении пользователя"""
        await self.send(text_data=json.dumps(event))
    
    async def user_disconnect(self, event):
        """Отправка сообщения об отключении пользователя"""
        await self.send(text_data=json.dumps(event))
    
    async def chat_message(self, event):
        """Отправка сообщения чата"""
        await self.send(text_data=json.dumps(event))
    
    async def player_status(self, event):
        """Отправка обновления статуса игрока"""
        await self.send(text_data=json.dumps(event))
    
    async def attribute_revealed(self, event):
        """Отправка информации о раскрытом атрибуте"""
        await self.send(text_data=json.dumps(event))
    
    async def vote_cast(self, event):
        """Отправка информации о голосовании"""
        await self.send(text_data=json.dumps(event))
    
    async def player_eliminated(self, event):
        """Отправка информации об исключении игрока"""
        await self.send(text_data=json.dumps(event))
    
    async def new_round(self, event):
        """Отправка информации о новом раунде"""
        await self.send(text_data=json.dumps(event))
    
    async def card_used(self, event):
        """Отправка информации об использовании карты"""
        await self.send(text_data=json.dumps(event))
    
    async def next_player(self, event):
        """Отправка информации о следующем игроке"""
        await self.send(text_data=json.dumps(event))
    
    # Вспомогательные методы для работы с базой данных
    
    @database_sync_to_async
    def is_user_in_room(self):
        """Проверяет, находится ли пользователь в комнате"""
        try:
            return Player.objects.filter(user=self.user, room__room_id=self.room_id).exists()
        except:
            return False
    
    @database_sync_to_async
    def is_player_owner(self, player_id):
        """Проверяет, принадлежит ли игрок текущему пользователю"""
        try:
            return Player.objects.filter(id=player_id, user=self.user).exists()
        except:
            return False
    
    @database_sync_to_async
    def save_chat_message(self, message):
        """Сохраняет сообщение чата в базе данных"""
        room = GameRoom.objects.get(room_id=self.room_id)
        return ChatMessage.objects.create(
            room=room,
            user=self.user,
            message=message
        )
    
    @database_sync_to_async
    def update_player_ready(self, player_id, ready):
        """Обновляет статус готовности игрока"""
        from .services import GameService
        return GameService.set_player_ready(player_id, ready)
    
    @database_sync_to_async
    def reveal_player_attribute(self, player_id, attribute):
        """Раскрывает атрибут игрока"""
        from .services import GameService
        success, message = GameService.reveal_attribute(player_id, attribute)
        
        # Получаем значение атрибута
        value = None
        if success:
            player = Player.objects.get(id=player_id)
            if attribute == 'age':
                value = player.age
            elif attribute == 'gender':
                value = player.gender
            elif attribute == 'child_free':
                value = player.child_free
            elif attribute == 'profession':
                value = player.profession.value if player.profession else None
            elif attribute == 'health':
                value = player.health.value if player.health else None
            elif attribute == 'baggage':
                value = player.baggage.value if player.baggage else None
            elif attribute == 'phobia':
                value = player.phobia.value if player.phobia else None
            elif attribute == 'fact1':
                value = player.fact1.value if player.fact1 else None
            elif attribute == 'fact2':
                value = player.fact2.value if player.fact2 else None
        
        return success, message, value
    
    @database_sync_to_async
    def vote_for_player(self, session_id, voter_id, target_id):
        """Голосует за исключение игрока"""
        from .services import GameService
        success, message = GameService.vote_player(session_id, voter_id, target_id)
        
        # Проверяем, произошло ли исключение игрока или переход к новому раунду
        elimination_data = None
        if success and ("исключен" in message or "раунд" in message):
            session = GameSession.objects.get(id=session_id)
            
            # Если игрок был исключен
            if "исключен" in message:
                eliminated_username = message.split()[1]
                eliminated_player = Player.objects.get(user__username=eliminated_username)
                
                elimination_data = {
                    'eliminated': True,
                    'player_id': eliminated_player.id,
                    'username': eliminated_username,
                    'round': session.current_round - 1
                }
            # Если начался новый раунд
            elif "раунд" in message:
                elimination_data = {
                    'eliminated': False,
                    'round': session.current_round,
                    'clockwise': session.clockwise
                }
        
        return success, message, elimination_data
    
    @database_sync_to_async
    def use_player_card(self, card_id, player_id, target_id, additional_data):
        """Использует карту действия"""
        from .services import GameService
        success, message = GameService.use_action_card(card_id, player_id, target_id, additional_data)
        
        # Получаем данные об эффекте карты
        effect_data = None
        if success:
            from .models import PlayerActionCard, ActionCard
            card = PlayerActionCard.objects.get(id=card_id).card
            effect_data = {
                'type': card.effect_type,
                'data': card.effect_data
            }
        
        return success, message, effect_data
    
    @database_sync_to_async
    def get_next_player(self, session_id):
        """Получает следующего игрока для хода"""
        from .services import GameService
        player, message =  GameService.get_next_player(session_id)
        return {
            'id': player.id,
            'username': player.user.username,
            'message': message
        }, message



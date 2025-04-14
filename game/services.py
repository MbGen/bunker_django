"""
Сервисные функции для игровой логики
"""
import random
import json
import os
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import (
    Catastrophe, CharacterAttribute, ActionCard, GameRoom, 
    PlayerProfile, GameSession, Player, PlayerActionCard, 
    Vote, GameEvent, GameConfiguration
)

class GameService:
    """Сервисный класс для основной игровой логики"""
    
    @staticmethod
    def create_game_room(creator, name, max_players=12):
        """Создает новую игровую комнату"""
        room = GameRoom.objects.create(
            creator=creator,
            name=name,
            max_players=max_players,
            status='waiting'
        )
        return room
    
    @staticmethod
    def join_game_room(user, room_id):
        """Добавляет пользователя в игровую комнату"""
        try:
            room = GameRoom.objects.get(room_id=room_id)
            
            # Проверяем, не заполнена ли комната
            if room.players.count() >= room.max_players:
                return None, "Комната заполнена"
            
            # Проверяем, не началась ли уже игра
            if room.status != 'waiting':
                return None, "Игра уже началась"
            
            # Проверяем, не присоединился ли уже пользователь
            if room.players.filter(user=user).exists():
                return room.players.get(user=user), "Вы уже присоединились к этой комнате"
            
            # Создаем игрока
            player = Player.objects.create(
                user=user,
                room=room,
                status='waiting',
                order=room.players.count()
            )
            
            return player, "Вы успешно присоединились к комнате"
        except GameRoom.DoesNotExist:
            return None, "Комната не найдена"
    
    @staticmethod
    def set_player_ready(player_id, ready=True):
        """Устанавливает статус готовности игрока"""
        try:
            player = Player.objects.get(id=player_id)
            player.status = 'ready' if ready else 'waiting'
            player.save()
            return True, "Статус готовности обновлен"
        except Player.DoesNotExist:
            return False, "Игрок не найден"
    
    @staticmethod
    def kick_player(room, player_to_kick):
        """Исключает игрока из комнаты (только для создателя)"""
        if player_to_kick.room != room:
            return False, "Игрок не находится в этой комнате"
        
        player_to_kick.delete()
        return True, "Игрок исключен из комнаты"
    
    @staticmethod
    def start_game(room_id, user_id):
        """Начинает игру в комнате"""
        try:
            room = GameRoom.objects.get(room_id=room_id)
            user = room.creator
            
            # Проверяем, является ли пользователь создателем комнаты
            if user.id != user_id:
                return False, "Только создатель комнаты может начать игру"
            
            # Проверяем минимальное количество игроков
            player_count = room.players.count()
            if player_count < 0:  # TODO: Изменить на 6 после тестирования
                return False, "Для начала игры необходимо минимум 6 игроков"
            
            # Проверяем, все ли игроки готовы
            not_ready_count = room.players.exclude(status='ready').count()
            if not_ready_count > 0:
                return False, f"{not_ready_count} игроков не готовы"
            
            # Начинаем игру
            with transaction.atomic():
                # Выбираем случайную катастрофу
                catastrophes = Catastrophe.objects.all()
                if catastrophes.exists():
                    room.catastrophe = random.choice(catastrophes)
                else:
                    # Если катастроф нет в базе, создаем тестовую
                    room.catastrophe = Catastrophe.objects.create(
                        name="Ядерная война",
                        description="Мир погрузился в хаос после обмена ядерными ударами",
                        cause="Политический конфликт между сверхдержавами",
                        duration_months=36
                    )
                
                # Устанавливаем параметры бункера
                room.bunker_size = f"{random.randint(50, 200)} кв. метров"
                room.bunker_supplies = f"Запасы еды и воды на {random.randint(6, 24)} месяцев"
                room.bunker_capacity = GameRoom.get_bunker_capacity(room)
                room.status = 'in_progress'
                room.save()
                
                # Создаем игровую сессию
                session = GameSession.objects.create(
                    room=room,
                    current_round=1,
                    clockwise=True,
                    current_player_index=0
                )
                
                # Генерируем карточки персонажей и карты действий для игроков
                GameService._generate_player_cards(room)
                
                # Создаем событие начала игры
                first_player = room.players.order_by('order').first()
                GameEvent.objects.create(
                    session=session,
                    type='game_start',
                    player=first_player,
                    data={
                        'catastrophe': room.catastrophe.name,
                        'bunker_size': room.bunker_size,
                        'bunker_supplies': room.bunker_supplies,
                        'bunker_capacity': room.bunker_capacity,
                        'player_count': player_count
                    }
                )
                
                return True, "Игра успешно начата"
        except GameRoom.DoesNotExist:
            return False, "Комната не найдена"
    
    @staticmethod
    def _generate_player_cards(room):
        """Генерирует карточки персонажей и карты действий для игроков"""
        players = room.players.all()
        
        # Получаем атрибуты из базы данных
        professions = list(CharacterAttribute.objects.filter(type='profession'))
        health_states = list(CharacterAttribute.objects.filter(type='health'))
        baggages = list(CharacterAttribute.objects.filter(type='baggage'))
        phobias = list(CharacterAttribute.objects.filter(type='phobia'))
        facts = list(CharacterAttribute.objects.filter(type='fact'))
        
        # Если атрибутов недостаточно, создаем тестовые
        if not professions:
            professions = GameService._create_test_attributes('profession', [
                "Врач", "Инженер", "Учитель", "Программист", "Фермер", 
                "Военный", "Повар", "Строитель", "Ученый", "Психолог"
            ])
        
        if not health_states:
            health_states = GameService._create_test_attributes('health', [
                "Полностью здоров", "Диабет", "Астма", "Аллергия", "Близорукость",
                "Хроническая бессонница", "Отсутствие одной руки", "Глухота"
            ])
        
        if not baggages:
            baggages = GameService._create_test_attributes('baggage', [
                "Аптечка", "Набор инструментов", "Книга по выживанию", "Семена растений",
                "Фонарик с батарейками", "Оружие", "Радиоприемник", "Компас"
            ])
        
        if not phobias:
            phobias = GameService._create_test_attributes('phobia', [
                "Клаустрофобия", "Акрофобия", "Арахнофобия", "Никтофобия",
                "Социофобия", "Гемофобия", "Мизофобия", "Танатофобия"
            ])
        
        if not facts:
            facts = GameService._create_test_attributes('fact', [
                "Умеет играть на музыкальных инструментах", "Знает три иностранных языка",
                "Бывший спортсмен", "Имеет опыт выживания в дикой природе",
                "Страдает от бессонницы", "Вегетарианец", "Имеет фотографическую память",
                "Боится темноты", "Аллергия на пыльцу", "Умеет готовить без рецептов",
                "Коллекционирует старинные монеты", "Никогда не был за границей",
                "Имеет большую семью", "Выиграл в лотерею", "Пережил стихийное бедствие"
            ])
        
        # Получаем карты действий
        action_cards = list(ActionCard.objects.all())
        
        # Если карт действий недостаточно, создаем тестовые
        if len(action_cards) < len(players) * 2:
            action_cards = GameService._create_test_action_cards()
        
        # Перемешиваем атрибуты и карты
        random.shuffle(professions)
        random.shuffle(health_states)
        random.shuffle(baggages)
        random.shuffle(phobias)
        random.shuffle(facts)
        random.shuffle(action_cards)
        
        # Распределяем атрибуты и карты между игроками
        for i, player in enumerate(players):
            # Устанавливаем статус игрока
            player.status = 'playing'
            
            # Генерируем случайный возраст от 18 до 70
            player.age = random.randint(18, 70)
            
            # Генерируем случайный пол
            player.gender = random.choice(['Мужской', 'Женский'])
            
            # Генерируем child_free статус
            player.child_free = random.choice([True, False])
            
            # Назначаем атрибуты персонажа
            player.profession = professions[i % len(professions)]
            player.health = health_states[i % len(health_states)]
            player.baggage = baggages[i % len(baggages)]
            player.phobia = phobias[i % len(phobias)]
            
            # Назначаем факты о персонаже
            fact_index1 = (i * 2) % len(facts)
            fact_index2 = (i * 2 + 1) % len(facts)
            player.fact1 = facts[fact_index1]
            player.fact2 = facts[fact_index2]
            
            player.save()
            
            # Раздаем карты действий (по 2 каждому игроку)
            for j in range(2):
                card_index = (i * 2 + j) % len(action_cards)
                PlayerActionCard.objects.create(
                    player=player,
                    card=action_cards[card_index],
                    used=False
                )
    
    @staticmethod
    def _create_test_attributes(attr_type, values):
        """Создает тестовые атрибуты персонажей"""
        attributes = []
        for value in values:
            attr = CharacterAttribute.objects.create(
                type=attr_type,
                value=value,
                description=f"Тестовое описание для {value}"
            )
            attributes.append(attr)
        return attributes
    
    @staticmethod
    def _create_test_action_cards():
        """Создает тестовые карты действий"""
        card_data = [
            {
                "name": "Смена профессии",
                "description": "Позволяет изменить профессию любого игрока",
                "effect_type": "change_attribute",
                "effect_data": {"attribute": "profession"}
            },
            {
                "name": "Обмен здоровьем",
                "description": "Позволяет обменяться состоянием здоровья с любым игроком",
                "effect_type": "swap_attribute",
                "effect_data": {"attribute": "health"}
            },
            {
                "name": "Дополнительный бункер",
                "description": "Рядом с основным бункером обнаружен дополнительный бункер на 2 человека",
                "effect_type": "add_bunker_capacity",
                "effect_data": {"capacity_increase": 2}
            },
            {
                "name": "Потеря припасов",
                "description": "Часть припасов в бункере испорчена, срок выживания сокращается",
                "effect_type": "reduce_supplies",
                "effect_data": {"months_reduction": 6}
            },
            {
                "name": "Дополнительные припасы",
                "description": "Обнаружены дополнительные припасы, срок выживания увеличивается",
                "effect_type": "increase_supplies",
                "effect_data": {"months_increase": 6}
            },
            {
                "name": "Раскрытие информации",
                "description": "Позволяет узнать один скрытый атрибут любого игрока",
                "effect_type": "reveal_attribute",
                "effect_data": {}
            },
            {
                "name": "Смена багажа",
                "description": "Позволяет изменить багаж любого игрока",
                "effect_type": "change_attribute",
                "effect_data": {"attribute": "baggage"}
            },
            {
                "name": "Иммунитет",
                "description": "Дает иммунитет от исключения на один раунд",
                "effect_type": "immunity",
                "effect_data": {"rounds": 1}
            },
            {
                "name": "Дополнительный голос",
                "description": "Дает дополнительный голос при голосовании в текущем раунде",
                "effect_type": "extra_vote",
                "effect_data": {"votes": 1}
            },
            {
                "name": "Вето",
                "description": "Позволяет отменить результаты голосования в текущем раунде",
                "effect_type": "veto",
                "effect_data": {}
            },
            {
                "name": "Смена фобии",
                "description": "Позволяет изменить фобию любого игрока",
                "effect_type": "change_attribute",
                "effect_data": {"attribute": "phobia"}
            },
            {
                "name": "Смена возраста",
                "description": "Позволяет изменить возраст любого игрока",
                "effect_type": "change_attribute",
                "effect_data": {"attribute": "age"}
            }
        ]
        
        cards = []
        for data in card_data:
            card = ActionCard.objects.create(
                name=data["name"],
                description=data["description"],
                effect_type=data["effect_type"],
                effect_data=data["effect_data"]
            )
            cards.append(card)
        
        return cards
    
    @staticmethod
    def reveal_attribute(player_id, attribute_name):
        """Открывает атрибут игрока для всех"""
        try:
            player = Player.objects.get(id=player_id)
            
            # Проверяем, не открыт ли уже атрибут
            if attribute_name in player.revealed_attributes:
                return False, "Этот атрибут уже открыт"
            
            # Проверяем, существует ли атрибут
            valid_attributes = ['age', 'gender', 'child_free', 'profession', 
                               'health', 'baggage', 'phobia', 'fact1', 'fact2']
            
            if attribute_name not in valid_attributes:
                return False, "Неверное название атрибута"
            
            # Открываем атрибут
            player.reveal_attribute(attribute_name)
            
            # Создаем событие раскрытия атрибута
            session = player.room.session
            GameEvent.objects.create(
                session=session,
                type='reveal',
                player=player,
                data={
                    'attribute': attribute_name,
                    'value': str(getattr(player, attribute_name))
                }
            )
            
            return True, f"Атрибут {attribute_name} успешно открыт"
        except Player.DoesNotExist:
            return False, "Игрок не найден"
    
    @staticmethod
    def vote_player(session_id, voter_id, target_id):
        """Голосование за исключение игрока"""
        try:
            session = GameSession.objects.get(id=session_id)
            voter = Player.objects.get(id=voter_id)
            target = Player.objects.get(id=target_id)
            
            # Проверяем, что игроки находятся в одной сессии
            if voter.room.id != session.room.id or target.room.id != session.room.id:
                return False, "Игроки не находятся в одной игровой сессии"
            
            # Проверяем, что игроки активны
            if voter.status != 'playing' or target.status != 'playing':
                return False, "Один из игроков не активен"
            
            # Проверяем, не голосовал ли уже игрок в этом раунде
            if Vote.objects.filter(session=session, round_number=session.current_round, voter=voter).exists():
                return False, "Вы уже голосовали в этом раунде"
            
            # Создаем голос
            vote = Vote.objects.create(
                session=session,
                round_number=session.current_round,
                voter=voter,
                target=target
            )
            
            # Создаем событие голосования
            GameEvent.objects.create(
                session=session,
                type='vote',
                player=voter,
                target_player=target,
                data={
                    'round': session.current_round
                }
            )
            
            # Проверяем, все ли игроки проголосовали
            active_players = Player.objects.filter(room=session.room, status='playing')
            votes_in_round = Vote.objects.filter(session=session, round_number=session.current_round)
            
            if votes_in_round.count() == active_players.count():
                # Все проголосовали, подсчитываем результаты
                return GameService._process_voting_results(session)
            
            return True, "Голос учтен"
        except (GameSession.DoesNotExist, Player.DoesNotExist):
            return False, "Сессия или игрок не найдены"
    
    @staticmethod
    def _process_voting_results(session):
        """Обрабатывает результаты голосования"""
        # Получаем все голоса в текущем раунде
        votes = Vote.objects.filter(session=session, round_number=session.current_round)
        
        # Подсчитываем голоса для каждого игрока
        vote_counts = {}
        for vote in votes:
            target_id = vote.target.id
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        # Находим игрока с наибольшим количеством голосов
        if not vote_counts:
            return True, "Никто не проголосовал"
        
        max_votes = max(vote_counts.values())
        players_with_max_votes = [player_id for player_id, count in vote_counts.items() if count == max_votes]
        
        # Если несколько игроков имеют одинаковое количество голосов, выбираем случайного
        eliminated_player_id = random.choice(players_with_max_votes)
        
        try:
            eliminated_player = Player.objects.get(id=eliminated_player_id)
            
            # Исключаем игрока
            eliminated_player.status = 'eliminated'
            eliminated_player.save()
            
            # Создаем событие исключения
            GameEvent.objects.create(
                session=session,
                type='elimination',
                player=eliminated_player,
                data={
                    'round': session.current_round,
                    'votes': max_votes
                }
            )
            
            # Проверяем, достигнуто ли необходимое количество выживших
            active_players = Player.objects.filter(room=session.room, status='playing')
            if active_players.count() <= session.room.bunker_capacity:
                # Игра завершена, все оставшиеся игроки выживают
                return GameService._end_game(session)
            
            # Переходим к следующему раунду
            session.current_round += 1
            session.clockwise = not session.clockwise  # Меняем направление хода
            session.save()
            
            return True, f"Игрок {eliminated_player.user.username} исключен. Начинается раунд {session.current_round}"
        except Player.DoesNotExist:
            return False, "Игрок не найден"
    
    @staticmethod
    def _end_game(session):
        """Завершает игру и определяет результат"""
        room = session.room
        
        # Отмечаем всех оставшихся игроков как выживших
        surviving_players = Player.objects.filter(room=room, status='playing')
        for player in surviving_players:
            player.status = 'survived'
            player.save()
        
        # Определяем результат игры на основе профессий выживших и катастрофы
        result = GameService._determine_survival_result(room, surviving_players)
        
        # Обновляем статус комнаты и сессии
        room.status = 'finished'
        room.save()
        
        session.finished_at = timezone.now()
        session.result = result
        session.save()
        
        # Создаем событие окончания игры
        GameEvent.objects.create(
            session=session,
            type='game_end',
            player=surviving_players.first(),
            data={
                'survivors': list(surviving_players.values_list('user__username', flat=True)),
                'result': result
            }
        )
        
        return True, f"Игра завершена. {result}"
    
    @staticmethod
    def _determine_survival_result(room, surviving_players):
        """Определяет результат выживания на основе профессий и катастрофы"""
        # Получаем профессии выживших
        professions = [player.profession.value for player in surviving_players if player.profession]
        
        # Базовый шанс выживания
        survival_chance = 50
        
        # Анализируем профессии и их полезность в контексте катастрофы
        useful_professions = {
            "Врач": 15,
            "Инженер": 15,
            "Фермер": 15,
            "Военный": 10,
            "Ученый": 15,
            "Строитель": 10,
            "Психолог": 5,
            "Повар": 5,
            "Учитель": 5,
            "Программист": 5
        }
        
        # Увеличиваем шанс выживания на основе полезных профессий
        for profession in professions:
            if profession in useful_professions:
                survival_chance += useful_professions[profession]
        
        # Учитываем разнообразие профессий
        unique_professions = set(professions)
        survival_chance += len(unique_professions) * 5
        
        # Учитываем катастрофу
        if room.catastrophe:
            catastrophe_name = room.catastrophe.name.lower()
            
            # Специфические бонусы в зависимости от катастрофы
            if "ядер" in catastrophe_name:
                if "Врач" in professions:
                    survival_chance += 10
                if "Инженер" in professions:
                    survival_chance += 10
            elif "эпидем" in catastrophe_name or "вирус" in catastrophe_name:
                if "Врач" in professions:
                    survival_chance += 20
                if "Ученый" in professions:
                    survival_chance += 15
            elif "наводнен" in catastrophe_name:
                if "Инженер" in professions:
                    survival_chance += 15
                if "Строитель" in professions:
                    survival_chance += 10
            elif "вулкан" in catastrophe_name or "землетряс" in catastrophe_name:
                if "Строитель" in professions:
                    survival_chance += 15
                if "Инженер" in professions:
                    survival_chance += 10
            elif "войн" in catastrophe_name:
                if "Военный" in professions:
                    survival_chance += 20
                if "Врач" in professions:
                    survival_chance += 10
            elif "голод" in catastrophe_name:
                if "Фермер" in professions:
                    survival_chance += 20
                if "Повар" in professions:
                    survival_chance += 15
        
        # Определяем результат
        if survival_chance >= 100:
            result = "Выжили! Благодаря идеальному сочетанию навыков и профессий, группа смогла не только выжить, но и создать основу для восстановления общества."
        elif survival_chance >= 80:
            result = "Выжили с трудностями. Группа смогла преодолеть большинство проблем и выжить, хотя и с некоторыми потерями."
        elif survival_chance >= 60:
            result = "Выжили, но едва. Группе удалось продержаться минимальный срок, но будущее остается неопределенным."
        elif survival_chance >= 40:
            result = "Не выжили. Несмотря на все усилия, группе не хватило ключевых навыков и ресурсов для долгосрочного выживания."
        else:
            result = "Катастрофа. Группа не смогла организовать эффективное сосуществование и использование ресурсов, что привело к быстрой гибели."
        
        return result
    
    @staticmethod
    def use_action_card(card_id, player_id, target_id=None, additional_data=None):
        """Использует карту действия"""
        try:
            player_card = PlayerActionCard.objects.get(id=card_id, player_id=player_id, used=False)
            player = player_card.player
            card = player_card.card
            room = player.room
            session = room.session
            
            # Проверяем, активна ли игра
            if room.status != 'in_progress':
                return False, "Игра не активна"
            
            # Проверяем, активен ли игрок
            if player.status != 'playing':
                return False, "Вы не можете использовать карту"
            
            # Обрабатываем эффект карты в зависимости от типа
            result_success = False
            result_message = "Неизвестный тип карты"
            
            if card.effect_type == 'change_attribute':
                result_success, result_message = GameService._effect_change_attribute(
                    card, player, target_id, additional_data, session
                )
            elif card.effect_type == 'swap_attribute':
                result_success, result_message = GameService._effect_swap_attribute(
                    card, player, target_id, session
                )
            elif card.effect_type == 'add_bunker_capacity':
                result_success, result_message = GameService._effect_add_bunker_capacity(
                    card, room, session, player
                )
            elif card.effect_type == 'reduce_supplies' or card.effect_type == 'increase_supplies':
                result_success, result_message = GameService._effect_modify_supplies(
                    card, room, session, player
                )
            elif card.effect_type == 'reveal_attribute':
                result_success, result_message = GameService._effect_reveal_attribute(
                    card, player, target_id, additional_data, session
                )
            elif card.effect_type == 'immunity':
                result_success, result_message = GameService._effect_immunity(
                    card, player, session
                )
            elif card.effect_type == 'extra_vote':
                result_success, result_message = GameService._effect_extra_vote(
                    card, player, session
                )
            elif card.effect_type == 'veto':
                result_success, result_message = GameService._effect_veto(
                    card, player, session
                )
            
            if result_success:
                # Отмечаем карту как использованную
                player_card.used = True
                player_card.save()
                
                # Создаем событие использования карты
                GameEvent.objects.create(
                    session=session,
                    type='action_card',
                    player=player,
                    target_player_id=target_id,
                    data={
                        'card_name': card.name,
                        'effect_type': card.effect_type,
                        'additional_data': additional_data
                    }
                )
            
            return result_success, result_message
        except PlayerActionCard.DoesNotExist:
            return False, "Карта не найдена или уже использована"
    
    @staticmethod
    def _effect_change_attribute(card, player, target_id, additional_data, session):
        """Эффект изменения атрибута"""
        try:
            if not target_id or not additional_data or 'new_value' not in additional_data:
                return False, "Недостаточно данных для применения карты"
            
            target = Player.objects.get(id=target_id, room=player.room)
            attribute = card.effect_data.get('attribute')
            new_value = additional_data.get('new_value')
            
            if attribute not in ['profession', 'health', 'baggage', 'phobia', 'age']:
                return False, "Неверный атрибут"
            
            if attribute == 'age':
                # Для возраста просто меняем значение
                if not new_value.isdigit() or int(new_value) < 18 or int(new_value) > 70:
                    return False, "Неверное значение возраста (должно быть от 18 до 70)"
                
                target.age = int(new_value)
                target.save()
                return True, f"Возраст игрока {target.user.username} изменен на {new_value}"
            else:
                # Для других атрибутов создаем новый или используем существующий
                try:
                    attr_obj = CharacterAttribute.objects.get(type=attribute, value=new_value)
                except CharacterAttribute.DoesNotExist:
                    attr_obj = CharacterAttribute.objects.create(
                        type=attribute,
                        value=new_value,
                        description=f"Создано картой действия"
                    )
                
                # Устанавливаем новый атрибут
                setattr(target, attribute, attr_obj)
                target.save()
                
                return True, f"Атрибут {attribute} игрока {target.user.username} изменен на {new_value}"
        except Player.DoesNotExist:
            return False, "Целевой игрок не найден"
    
    @staticmethod
    def _effect_swap_attribute(card, player, target_id, session):
        """Эффект обмена атрибутами"""
        try:
            if not target_id:
                return False, "Не указан целевой игрок"
            
            target = Player.objects.get(id=target_id, room=player.room)
            attribute = card.effect_data.get('attribute')
            
            if attribute not in ['profession', 'health', 'baggage', 'phobia']:
                return False, "Неверный атрибут для обмена"
            
            # Обмениваем атрибуты
            player_attr = getattr(player, attribute)
            target_attr = getattr(target, attribute)
            
            setattr(player, attribute, target_attr)
            setattr(target, attribute, player_attr)
            
            player.save()
            target.save()
            
            return True, f"Вы обменялись атрибутом {attribute} с игроком {target.user.username}"
        except Player.DoesNotExist:
            return False, "Целевой игрок не найден"
    
    @staticmethod
    def _effect_add_bunker_capacity(card, room, session, player):
        """Эффект увеличения вместимости бункера"""
        capacity_increase = card.effect_data.get('capacity_increase', 2)
        
        room.bunker_capacity += capacity_increase
        room.save()
        
        return True, f"Вместимость бункера увеличена на {capacity_increase}. Новая вместимость: {room.bunker_capacity}"
    
    @staticmethod
    def _effect_modify_supplies(card, room, session, player):
        """Эффект изменения запасов"""
        if card.effect_type == 'reduce_supplies':
            months_change = -card.effect_data.get('months_reduction', 6)
            message = f"Запасы в бункере уменьшены на {abs(months_change)} месяцев"
        else:  # increase_supplies
            months_change = card.effect_data.get('months_increase', 6)
            message = f"Запасы в бункере увеличены на {months_change} месяцев"
        
        # Обновляем описание запасов
        current_supplies = room.bunker_supplies
        if "месяцев" in current_supplies:
            try:
                parts = current_supplies.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        current_months = int(part)
                        new_months = max(1, current_months + months_change)
                        parts[i] = str(new_months)
                        break
                
                room.bunker_supplies = " ".join(parts)
                room.save()
                
                return True, message + f". Новые запасы: {room.bunker_supplies}"
            except:
                pass
        
        # Если не удалось обновить, просто добавляем информацию
        room.bunker_supplies += f" ({message})"
        room.save()
        
        return True, message
    
    @staticmethod
    def _effect_reveal_attribute(card, player, target_id, additional_data, session):
        """Эффект раскрытия атрибута"""
        try:
            if not target_id or not additional_data or 'attribute' not in additional_data:
                return False, "Недостаточно данных для применения карты"
            
            target = Player.objects.get(id=target_id, room=player.room)
            attribute = additional_data.get('attribute')
            
            # Проверяем, не открыт ли уже атрибут
            if attribute in target.revealed_attributes:
                return False, "Этот атрибут уже открыт"
            
            # Проверяем, существует ли атрибут
            valid_attributes = ['age', 'gender', 'child_free', 'profession', 
                               'health', 'baggage', 'phobia', 'fact1', 'fact2']
            
            if attribute not in valid_attributes:
                return False, "Неверное название атрибута"
            
            # Открываем атрибут
            target.reveal_attribute(attribute)
            
            return True, f"Атрибут {attribute} игрока {target.user.username} раскрыт"
        except Player.DoesNotExist:
            return False, "Целевой игрок не найден"
    
    @staticmethod
    def _effect_immunity(card, player, session):
        """Эффект иммунитета от исключения"""
        rounds = card.effect_data.get('rounds', 1)
        
        # Добавляем информацию об иммунитете в данные игрока
        player_data = player.data if hasattr(player, 'data') else {}
        immunity_until = session.current_round + rounds
        
        if not hasattr(player, 'data'):
            player.data = {}
        
        player.data['immunity_until'] = immunity_until
        player.save()
        
        return True, f"Вы получили иммунитет от исключения на {rounds} раунд(ов)"
    
    @staticmethod
    def _effect_extra_vote(card, player, session):
        """Эффект дополнительного голоса"""
        votes = card.effect_data.get('votes', 1)
        
        # Добавляем информацию о дополнительных голосах
        if not hasattr(player, 'data'):
            player.data = {}
        
        player.data['extra_votes'] = player.data.get('extra_votes', 0) + votes
        player.save()
        
        return True, f"Вы получили {votes} дополнительных голосов в текущем раунде"
    
    @staticmethod
    def _effect_veto(card, player, session):
        """Эффект вето на результаты голосования"""
        # Отменяем все голоса в текущем раунде
        Vote.objects.filter(session=session, round_number=session.current_round).delete()
        
        # Переходим к следующему раунду
        session.current_round += 1
        session.save()
        
        return True, f"Результаты голосования отменены. Начинается раунд {session.current_round}"
    
    @staticmethod
    def get_next_player(session_id):
        """Получает следующего игрока для хода"""
        try:
            session = GameSession.objects.get(id=session_id)
            room = session.room
            
            # Получаем активных игроков, отсортированных по порядку
            active_players = list(Player.objects.filter(
                room=room, 
                status='playing'
            ).order_by('order'))
            
            if not active_players:
                return None, "Нет активных игроков"
            
            # Определяем текущий индекс
            current_index = session.current_player_index
            
            # Определяем следующий индекс в зависимости от направления
            if session.clockwise:
                next_index = (current_index + 1) % len(active_players)
            else:
                next_index = (current_index - 1) % len(active_players)
            
            # Обновляем индекс в сессии
            session.current_player_index = next_index
            session.save()
            
            return active_players[next_index], "Следующий игрок определен"
        except GameSession.DoesNotExist:
            return None, "Сессия не найдена"
    
    @staticmethod
    def skip_elimination(session_id):
        """Пропускает исключение в текущем раунде"""
        try:
            session = GameSession.objects.get(id=session_id)
            
            # Переходим к следующему раунду
            session.current_round += 1
            session.clockwise = not session.clockwise  # Меняем направление хода
            session.save()
            
            # Создаем событие пропуска исключения
            first_player = Player.objects.filter(room=session.room, status='playing').first()
            GameEvent.objects.create(
                session=session,
                type='vote',
                player=first_player,
                data={
                    'round': session.current_round - 1,
                    'skipped': True
                }
            )
            
            return True, f"Исключение пропущено. Начинается раунд {session.current_round}"
        except GameSession.DoesNotExist:
            return False, "Сессия не найдена"
    
    @staticmethod
    def load_game_configuration():
        """Загружает конфигурацию игры из JSON-файлов"""
        config_dir = os.path.join(settings.BASE_DIR, 'game_config')
        
        # Создаем директорию, если она не существует
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Загружаем конфигурацию катастроф
        catastrophes_file = os.path.join(config_dir, 'catastrophes.json')
        if os.path.exists(catastrophes_file):
            try:
                with open(catastrophes_file, 'r', encoding='utf-8') as f:
                    catastrophes_data = json.load(f)
                
                for cat_data in catastrophes_data:
                    Catastrophe.objects.get_or_create(
                        name=cat_data['name'],
                        defaults={
                            'description': cat_data['description'],
                            'cause': cat_data['cause'],
                            'duration_months': cat_data['duration_months']
                        }
                    )
            except Exception as e:
                print(f"Ошибка загрузки катастроф: {e}")
        
        # Загружаем конфигурацию атрибутов
        attributes_file = os.path.join(config_dir, 'attributes.json')
        if os.path.exists(attributes_file):
            try:
                with open(attributes_file, 'r', encoding='utf-8') as f:
                    attributes_data = json.load(f)
                
                for attr_type, values in attributes_data.items():
                    for value in values:
                        if isinstance(value, dict):
                            CharacterAttribute.objects.get_or_create(
                                type=attr_type,
                                value=value['value'],
                                defaults={
                                    'description': value.get('description', '')
                                }
                            )
                        else:
                            CharacterAttribute.objects.get_or_create(
                                type=attr_type,
                                value=value
                            )
            except Exception as e:
                print(f"Ошибка загрузки атрибутов: {e}")
        
        # Загружаем конфигурацию карт действий
        action_cards_file = os.path.join(config_dir, 'action_cards.json')
        if os.path.exists(action_cards_file):
            try:
                with open(action_cards_file, 'r', encoding='utf-8') as f:
                    cards_data = json.load(f)
                
                for card_data in cards_data:
                    ActionCard.objects.get_or_create(
                        name=card_data['name'],
                        defaults={
                            'description': card_data['description'],
                            'effect_type': card_data['effect_type'],
                            'effect_data': card_data['effect_data']
                        }
                    )
            except Exception as e:
                print(f"Ошибка загрузки карт действий: {e}")
        
        return True, "Конфигурация загружена"
    
    @staticmethod
    def save_game_configuration():
        """Сохраняет текущую конфигурацию игры в JSON-файлы"""
        config_dir = os.path.join(settings.BASE_DIR, 'game_config')
        
        # Создаем директорию, если она не существует
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Сохраняем конфигурацию катастроф
        catastrophes = Catastrophe.objects.all()
        catastrophes_data = []
        
        for cat in catastrophes:
            catastrophes_data.append({
                'name': cat.name,
                'description': cat.description,
                'cause': cat.cause,
                'duration_months': cat.duration_months
            })
        
        catastrophes_file = os.path.join(config_dir, 'catastrophes.json')
        with open(catastrophes_file, 'w', encoding='utf-8') as f:
            json.dump(catastrophes_data, f, ensure_ascii=False, indent=4)
        
        # Сохраняем конфигурацию атрибутов
        attributes = CharacterAttribute.objects.all()
        attributes_data = {
            'profession': [],
            'health': [],
            'baggage': [],
            'phobia': [],
            'fact': []
        }
        
        for attr in attributes:
            attr_data = {
                'value': attr.value
            }
            if attr.description:
                attr_data['description'] = attr.description
            
            if attr.type in attributes_data:
                attributes_data[attr.type].append(attr_data)
        
        attributes_file = os.path.join(config_dir, 'attributes.json')
        with open(attributes_file, 'w', encoding='utf-8') as f:
            json.dump(attributes_data, f, ensure_ascii=False, indent=4)
        
        # Сохраняем конфигурацию карт действий
        action_cards = ActionCard.objects.all()
        cards_data = []
        
        for card in action_cards:
            cards_data.append({
                'name': card.name,
                'description': card.description,
                'effect_type': card.effect_type,
                'effect_data': card.effect_data
            })
        
        action_cards_file = os.path.join(config_dir, 'action_cards.json')
        with open(action_cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=4)
        
        return True, "Конфигурация сохранена"

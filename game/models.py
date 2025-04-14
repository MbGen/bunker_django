from django.db import models
from django.contrib.auth.models import User
import json
import random
import uuid

class Catastrophe(models.Model):
    """Модель для катастроф"""
    name = models.CharField(max_length=100, verbose_name="Название катастрофы")
    description = models.TextField(verbose_name="Описание катастрофы")
    cause = models.TextField(verbose_name="Причина катастрофы")
    duration_months = models.IntegerField(verbose_name="Продолжительность (месяцев)")
    effects = models.JSONField(default=list, verbose_name="Эффекты катастрофы")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Катастрофа"
        verbose_name_plural = "Катастрофы"

class CharacterAttribute(models.Model):
    """Базовая модель для атрибутов персонажа"""
    TYPE_CHOICES = (
        ('profession', 'Профессия'),
        ('health', 'Здоровье'),
        ('baggage', 'Багаж'),
        ('phobia', 'Фобия'),
        ('fact', 'Факт о персонаже'),
    )
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Тип атрибута")
    value = models.CharField(max_length=255, verbose_name="Значение")
    description = models.TextField(blank=True, null=True, verbose_name="Дополнительное описание")
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.value}"
    
    class Meta:
        verbose_name = "Атрибут персонажа"
        verbose_name_plural = "Атрибуты персонажей"

class Profession(models.Model):
    """Модель для профессий персонажей"""
    value = models.CharField(max_length=255, verbose_name="Название профессии")
    description = models.TextField(verbose_name="Описание профессии")
    category = models.CharField(max_length=100, verbose_name="Категория")
    usefulness = models.IntegerField(verbose_name="Полезность")
    
    def __str__(self):
        return self.value
    
    class Meta:
        verbose_name = "Профессия"
        verbose_name_plural = "Профессии"

class HealthState(models.Model):
    """Модель для состояний здоровья персонажей"""
    value = models.CharField(max_length=255, verbose_name="Название состояния")
    description = models.TextField(verbose_name="Описание состояния")
    category = models.CharField(max_length=100, verbose_name="Категория")
    survival_factor = models.IntegerField(verbose_name="Фактор выживания")
    
    def __str__(self):
        return self.value
    
    class Meta:
        verbose_name = "Состояние здоровья"
        verbose_name_plural = "Состояния здоровья"

class Baggage(models.Model):
    """Модель для багажа персонажей"""
    value = models.CharField(max_length=255, verbose_name="Название предмета")
    description = models.TextField(verbose_name="Описание предмета")
    category = models.CharField(max_length=100, verbose_name="Категория")
    usefulness = models.IntegerField(verbose_name="Полезность")
    
    def __str__(self):
        return self.value
    
    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багаж"

class Phobia(models.Model):
    """Модель для фобий персонажей"""
    value = models.CharField(max_length=255, verbose_name="Название фобии")
    description = models.TextField(verbose_name="Описание фобии")
    category = models.CharField(max_length=100, verbose_name="Категория")
    impact = models.IntegerField(verbose_name="Влияние")
    
    def __str__(self):
        return self.value
    
    class Meta:
        verbose_name = "Фобия"
        verbose_name_plural = "Фобии"

class Fact(models.Model):
    """Модель для фактов о персонажах"""
    value = models.CharField(max_length=255, verbose_name="Название факта")
    description = models.TextField(verbose_name="Описание факта")
    category = models.CharField(max_length=100, verbose_name="Категория")
    usefulness = models.IntegerField(verbose_name="Полезность")
    
    def __str__(self):
        return self.value
    
    class Meta:
        verbose_name = "Факт"
        verbose_name_plural = "Факты"

class ActionCard(models.Model):
    """Модель для карт действий"""
    name = models.CharField(max_length=100, verbose_name="Название карты")
    description = models.TextField(verbose_name="Описание действия")
    effect_type = models.CharField(max_length=50, verbose_name="Тип эффекта")
    effect_data = models.JSONField(default=dict, verbose_name="Данные эффекта")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Карта действия"
        verbose_name_plural = "Карты действий"

class GameRoom(models.Model):
    """Модель для игровых комнат"""
    STATUS_CHOICES = (
        ('waiting', 'Ожидание игроков'),
        ('in_progress', 'Игра идет'),
        ('finished', 'Игра завершена'),
    )
    id = models.AutoField(primary_key=True)    
    room_id = models.CharField(max_length=10, unique=True, default=uuid.uuid4().hex[:8], verbose_name="ID комнаты")
    name = models.CharField(max_length=100, verbose_name="Название комнаты")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms', verbose_name="Создатель")
    max_players = models.IntegerField(default=12, verbose_name="Максимальное количество игроков")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    catastrophe = models.ForeignKey(Catastrophe, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Катастрофа")
    bunker_size = models.CharField(max_length=100, blank=True, null=True, verbose_name="Размер бункера")
    bunker_supplies = models.TextField(blank=True, null=True, verbose_name="Запасы в бункере")
    bunker_capacity = models.IntegerField(default=0, verbose_name="Вместимость бункера")
    
    def __str__(self):
        return f"{self.name} ({self.room_id})"
    
    def get_bunker_capacity(self):
        """Рассчитывает вместимость бункера на основе количества игроков"""
        # player_count = self.players.count()
        player_count = self.max_players
        if player_count % 2 == 0:
            return player_count // 2
        else:
            return (player_count // 2) + 1
    
    def save(self, *args, **kwargs):
        if not self.bunker_capacity:
            self.bunker_capacity = self.get_bunker_capacity()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Игровая комната"
        verbose_name_plural = "Игровые комнаты"

class PlayerProfile(models.Model):
    """Модель для профилей игроков"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь")
    nickname = models.CharField(max_length=50, verbose_name="Никнейм")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    
    def __str__(self):
        return self.nickname
    
    class Meta:
        verbose_name = "Профиль игрока"
        verbose_name_plural = "Профили игроков"

class GameSession(models.Model):
    """Модель для игровых сессий"""
    room = models.OneToOneField(GameRoom, on_delete=models.CASCADE, related_name='session', verbose_name="Комната")
    current_round = models.IntegerField(default=1, verbose_name="Текущий раунд")
    clockwise = models.BooleanField(default=True, verbose_name="Направление хода (по часовой)")
    current_player_index = models.IntegerField(default=0, verbose_name="Индекс текущего игрока")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Время начала")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания")
    result = models.TextField(blank=True, null=True, verbose_name="Результат игры")
    
    def __str__(self):
        return f"Сессия {self.room.room_id}"
    
    class Meta:
        verbose_name = "Игровая сессия"
        verbose_name_plural = "Игровые сессии"

class Player(models.Model):
    """Модель для игроков в конкретной игровой сессии"""
    STATUS_CHOICES = (
        ('waiting', 'Ожидание'),
        ('ready', 'Готов'),
        ('playing', 'Играет'),
        ('eliminated', 'Исключен'),
        ('survived', 'Выжил'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='players', verbose_name="Комната")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', verbose_name="Статус")
    order = models.IntegerField(default=0, verbose_name="Порядок хода")
    
    # Атрибуты персонажа
    age = models.IntegerField(null=True, blank=True, verbose_name="Возраст")
    gender = models.CharField(max_length=20, null=True, blank=True, verbose_name="Пол")
    child_free = models.BooleanField(default=False, verbose_name="Child free")
    profession = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='profession_players', verbose_name="Профессия")
    health = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='health_players', verbose_name="Здоровье")
    baggage = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='baggage_players', verbose_name="Багаж")
    phobia = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='phobia_players', verbose_name="Фобия")
    fact1 = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='fact1_players', verbose_name="Факт 1")
    fact2 = models.ForeignKey(CharacterAttribute, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='fact2_players', verbose_name="Факт 2")
    
    # Открытые атрибуты
    revealed_attributes = models.JSONField(default=list, verbose_name="Открытые атрибуты")
    
    def __str__(self):
        return f"{self.user.username} в комнате {self.room.room_id}"
    
    def reveal_attribute(self, attribute_name):
        """Открывает атрибут для всех игроков"""
        if attribute_name not in self.revealed_attributes:
            self.revealed_attributes.append(attribute_name)
            self.save()
            return True
        return False
    
    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"
        unique_together = ('user', 'room')

class PlayerActionCard(models.Model):
    """Модель для карт действий у игроков"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='action_cards', verbose_name="Игрок")
    card = models.ForeignKey(ActionCard, on_delete=models.CASCADE, verbose_name="Карта действия")
    used = models.BooleanField(default=False, verbose_name="Использована")
    
    def __str__(self):
        return f"{self.card.name} ({self.player.user.username})"
    
    class Meta:
        verbose_name = "Карта действия игрока"
        verbose_name_plural = "Карты действий игроков"

class Vote(models.Model):
    """Модель для голосования"""
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='votes', verbose_name="Сессия")
    round_number = models.IntegerField(verbose_name="Номер раунда")
    voter = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_cast', verbose_name="Голосующий")
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_received', verbose_name="Цель голосования")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время голосования")
    
    def __str__(self):
        return f"{self.voter.user.username} голосует против {self.target.user.username} (Раунд {self.round_number})"
    
    class Meta:
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"
        unique_together = ('session', 'round_number', 'voter')

class GameEvent(models.Model):
    """Модель для игровых событий"""
    TYPE_CHOICES = (
        ('reveal', 'Раскрытие атрибута'),
        ('vote', 'Голосование'),
        ('elimination', 'Исключение игрока'),
        ('action_card', 'Использование карты действия'),
        ('game_start', 'Начало игры'),
        ('game_end', 'Конец игры'),
    )
    
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='events', verbose_name="Сессия")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Тип события")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='events', verbose_name="Игрок")
    target_player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True, 
                                     related_name='targeted_events', verbose_name="Цель события")
    data = models.JSONField(default=dict, verbose_name="Данные события")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время события")
    
    def __str__(self):
        return f"{self.get_type_display()} ({self.player.user.username})"
    
    class Meta:
        verbose_name = "Игровое событие"
        verbose_name_plural = "Игровые события"

class ChatMessage(models.Model):
    """Модель для сообщений чата"""
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='messages', verbose_name="Комната")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    message = models.TextField(verbose_name="Сообщение")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:20]}..."
    
    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        ordering = ['timestamp']

class GameConfiguration(models.Model):
    """Модель для хранения конфигурации игры"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Название конфигурации")
    config_type = models.CharField(max_length=50, verbose_name="Тип конфигурации")
    data = models.JSONField(verbose_name="Данные конфигурации")
    
    def __str__(self):
        return f"{self.name} ({self.config_type})"
    
    class Meta:
        verbose_name = "Конфигурация игры"
        verbose_name_plural = "Конфигурации игры"

from django.contrib import admin
from .models import (
    Catastrophe, Profession, HealthState, Baggage, 
    Phobia, Fact, ActionCard, GameRoom, Player, 
    GameSession, PlayerActionCard, Vote, GameEvent, ChatMessage
)

# Регистрация моделей конфигурации
@admin.register(Catastrophe)
class CatastropheAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'duration_months')
    search_fields = ('name', 'description')
    list_filter = ('duration_months',)

@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'category', 'usefulness')
    search_fields = ('value', 'description')
    list_filter = ('category', 'usefulness')

@admin.register(HealthState)
class HealthStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'category', 'survival_factor')
    search_fields = ('value', 'description')
    list_filter = ('category', 'survival_factor')

@admin.register(Baggage)
class BaggageAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'category', 'usefulness')
    search_fields = ('value', 'description')
    list_filter = ('category', 'usefulness')

@admin.register(Phobia)
class PhobiaAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'category', 'impact')
    search_fields = ('value', 'description')
    list_filter = ('category', 'impact')

@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'category', 'usefulness')
    search_fields = ('value', 'description')
    list_filter = ('category', 'usefulness')

@admin.register(ActionCard)
class ActionCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'effect_type')
    search_fields = ('name', 'description')
    list_filter = ('effect_type',)

# Регистрация моделей игры
@admin.register(GameRoom)
class GameRoomAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'name', 'creator', 'status', 'created_at')
    search_fields = ('room_id', 'name', 'creator__username')
    list_filter = ('status', 'created_at')
    readonly_fields = ('room_id', 'created_at')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'status')
    search_fields = ('user__username', 'room__room_id')
    list_filter = ('status',)

@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'current_round', 'started_at')
    search_fields = ('room__room_id', 'room__name')
    list_filter = ('started_at',)
    readonly_fields = ('started_at',)

@admin.register(PlayerActionCard)
class PlayerActionCardAdmin(admin.ModelAdmin):
    list_display = ('player', 'card', 'used')
    search_fields = ('player__user__username', 'card__name')
    list_filter = ('used',)

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('session', 'voter', 'target', 'round_number')
    search_fields = ('voter__user__username', 'target__user__username')
    list_filter = ('round_number',)

@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    list_display = ('session', 'type', 'player', 'target_player', 'timestamp')
    search_fields = ('player__user__username', 'target_player__user__username')
    list_filter = ('type', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'timestamp')
    search_fields = ('room__room_id', 'user__username', 'message')
    list_filter = ('timestamp',)
    readonly_fields = ('timestamp',)

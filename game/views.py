from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse
from django.contrib import messages
from .forms import CustomUserCreationForm

from .models import (
    GameRoom, Player, GameSession, PlayerActionCard, 
    Vote, GameEvent, ChatMessage, PlayerProfile
)

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Регистрация успешна! Теперь вы можете войти в систему.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'game/auth/register.html', {'form': form})
from .services import GameService

def index(request):
    """Главная страница"""
    return render(request, 'game/index.html')

@login_required
def create_game(request):
    """Страница создания игры"""
    if request.method == 'POST':
        name = request.POST.get('name', f'Комната {request.user.username}')
        max_players = int(request.POST.get('max_players', 12))
        
        # Создаем комнату
        room = GameService.create_game_room(request.user, name, max_players)
        
        # Создаем игрока для создателя
        player = Player.objects.create(
            user=request.user,
            room=room,
            status='waiting',
            order=0
        )
        
        return redirect('game_room', room_id=room.room_id)
    
    return render(request, 'game/create_game.html')

@login_required
def join_game(request):
    """Страница присоединения к игре"""
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        return redirect('join_game_by_id', room_id=room_id)
    
    return render(request, 'game/join_game.html')

@login_required
def join_game_by_id(request, room_id):
    """Присоединение к игре по ID"""
    player, message = GameService.join_game_room(request.user, room_id)
    
    if player:
        return redirect('game_room', room_id=room_id)
    else:
        # Если не удалось присоединиться, возвращаемся на страницу с сообщением об ошибке
        return render(request, 'game/join_game.html', {'error': message})

@login_required
def game_room(request, room_id):
    """Страница игровой комнаты"""
    room = get_object_or_404(GameRoom, room_id=room_id)
    # Проверяем, есть ли пользователь в комнате
    try:
        player = Player.objects.get(user=request.user, room=room)
    except Player.DoesNotExist:
        return redirect('join_game_by_id', room_id=room_id)
    
    # Получаем всех игроков в комнате
    players = room.players.all().order_by('order')
    
    # Если игра в процессе, получаем дополнительные данные
    game_data = {}
    if room.status == 'in_progress':
        # Получаем игровую сессию
        session = room.session
        
        # Получаем карты действий игрока
        action_cards = PlayerActionCard.objects.filter(player=player, used=False)
        
        # Получаем атрибуты персонажа
        character_attributes = {
            'age': player.age,
            'gender': player.gender,
            'child_free': player.child_free,
            'profession': player.profession.value if player.profession else None,
            'health': player.health.value if player.health else None,
            'baggage': player.baggage.value if player.baggage else None,
            'phobia': player.phobia.value if player.phobia else None,
            'fact1': player.fact1.value if player.fact1 else None,
            'fact2': player.fact2.value if player.fact2 else None,
        }
        
        # Получаем открытые атрибуты всех игроков
        revealed_attributes = {}
        for p in players:
            p_attrs = {}
            for attr in p.revealed_attributes:
                if attr == 'age':
                    p_attrs[attr] = p.age
                elif attr == 'gender':
                    p_attrs[attr] = p.gender
                elif attr == 'child_free':
                    p_attrs[attr] = p.child_free
                elif attr == 'profession':
                    p_attrs[attr] = p.profession.value if p.profession else None
                elif attr == 'health':
                    p_attrs[attr] = p.health.value if p.health else None
                elif attr == 'baggage':
                    p_attrs[attr] = p.baggage.value if p.baggage else None
                elif attr == 'phobia':
                    p_attrs[attr] = p.phobia.value if p.phobia else None
                elif attr == 'fact1':
                    p_attrs[attr] = p.fact1.value if p.fact1 else None
                elif attr == 'fact2':
                    p_attrs[attr] = p.fact2.value if p.fact2 else None
            
            revealed_attributes[p.id] = p_attrs
        
        # Получаем текущего игрока
        current_player = None
        if session.current_player_index < len(players.filter(status='playing')):
            current_player = players.filter(status='playing').order_by('order')[session.current_player_index]
        
        # Получаем последние события
        events = GameEvent.objects.filter(session=session).order_by('-timestamp')[:10]
        
        game_data = {
            'session': session,
            'action_cards': action_cards,
            'character_attributes': character_attributes,
            'revealed_attributes': revealed_attributes,
            'current_player': current_player,
            'events': events,
            'is_my_turn': current_player == player if current_player else False,
            'catastrophe': room.catastrophe,
            'bunker_info': {
                'size': room.bunker_size,
                'supplies': room.bunker_supplies,
                'capacity': room.bunker_capacity
            }
        }
    
    # Получаем сообщения чата
    chat_messages = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]
    
    context = {
        'room': room,
        'player': player,
        'players': players,
        'is_creator': room.creator == request.user,
        'game_data': game_data,
        'chat_messages': chat_messages
    }
    from pprint import pprint 
    pprint(f"CONTEXT: {context}")
    return render(request, 'game/game_room.html', context)

@login_required
@require_POST
def start_game(request, room_id):
    """Начало игры"""
    room = get_object_or_404(GameRoom, room_id=room_id)
    
    # Проверяем, является ли пользователь создателем комнаты
    if room.creator != request.user:
        return HttpResponseForbidden("Только создатель комнаты может начать игру")
    
    success, message = GameService.start_game(room_id, request.user.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        if success:
            return redirect('game_room', room_id=room_id)
        else:
            return render(request, 'game/game_room.html', {
                'room': room,
                'error': message
            })

@login_required
@require_POST
def kick_player(request, room_id, player_id):
    """Исключение игрока из комнаты"""
    room = get_object_or_404(GameRoom, room_id=room_id)
    player_to_kick = get_object_or_404(Player, id=player_id)
    
    # Проверяем, является ли пользователь создателем комнаты
    if room.creator != request.user:
        return HttpResponseForbidden("Только создатель комнаты может исключать игроков")
    
    success, message = GameService.kick_player(room, player_to_kick)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=room_id)

@login_required
def set_player_ready(request, player_id):
    """Установка статуса готовности игрока"""
    player = get_object_or_404(Player, id=player_id)
    
    # Проверяем, принадлежит ли игрок текущему пользователю
    if player.user != request.user:
        return HttpResponseForbidden("Вы можете изменять только свой статус")
    
    ready = request.GET.get('ready', 'true').lower() == 'true'
    success, message = GameService.set_player_ready(player_id, ready)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=player.room.room_id)

@login_required
def reveal_attribute(request, player_id, attribute):
    """Раскрытие атрибута персонажа"""
    player = get_object_or_404(Player, id=player_id)
    
    # Проверяем, принадлежит ли игрок текущему пользователю
    if player.user != request.user:
        return HttpResponseForbidden("Вы можете раскрывать только свои атрибуты")
    
    success, message = GameService.reveal_attribute(player_id, attribute)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=player.room.room_id)

@login_required
@require_POST
def vote_player(request, session_id, voter_id, target_id):
    """Голосование за исключение игрока"""
    voter = get_object_or_404(Player, id=voter_id)
    
    # Проверяем, принадлежит ли голосующий текущему пользователю
    if voter.user != request.user:
        return HttpResponseForbidden("Вы можете голосовать только от своего имени")
    
    success, message = GameService.vote_player(session_id, voter_id, target_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=voter.room.room_id)

@login_required
@require_POST
def skip_elimination(request, session_id):
    """Пропуск исключения в текущем раунде"""
    session = get_object_or_404(GameSession, id=session_id)
    
    # Проверяем, является ли пользователь создателем комнаты
    if session.room.creator != request.user:
        return HttpResponseForbidden("Только создатель комнаты может пропустить исключение")
    
    success, message = GameService.skip_elimination(session_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=session.room.room_id)

@login_required
@require_POST
def use_action_card(request, card_id, player_id):
    """Использование карты действия"""
    player = get_object_or_404(Player, id=player_id)
    
    # Проверяем, принадлежит ли игрок текущему пользователю
    if player.user != request.user:
        return HttpResponseForbidden("Вы можете использовать только свои карты")
    
    # Получаем дополнительные данные из запроса
    target_id = request.POST.get('target_id')
    additional_data = {}
    
    for key, value in request.POST.items():
        if key not in ['csrfmiddlewaretoken', 'target_id']:
            additional_data[key] = value
    
    success, message = GameService.use_action_card(card_id, player_id, target_id, additional_data)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})
    else:
        return redirect('game_room', room_id=player.room.room_id)

@login_required
def get_next_player(request, session_id):
    """Получение следующего игрока для хода"""
    session = get_object_or_404(GameSession, id=session_id)
    
    # Проверяем, находится ли пользователь в этой комнате
    if not Player.objects.filter(user=request.user, room=session.room).exists():
        return HttpResponseForbidden("Вы не участвуете в этой игре")
    
    player, message = GameService.get_next_player(session_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': player is not None,
            'message': message,
            'player': {
                'id': player.id,
                'username': player.user.username
            } if player else None
        })
    else:
        return redirect('game_room', room_id=session.room.room_id)

@login_required
def game_results(request, session_id):
    """Страница результатов игры"""
    session = get_object_or_404(GameSession, id=session_id)
    room = session.room
    
    # Проверяем, находится ли пользователь в этой комнате
    if not Player.objects.filter(user=request.user, room=room).exists():
        return HttpResponseForbidden("Вы не участвуете в этой игре")
    
    # Проверяем, завершена ли игра
    if room.status != 'finished':
        return redirect('game_room', room_id=room.room_id)
    
    # Получаем выживших игроков
    survivors = Player.objects.filter(room=room, status='survived')
    
    # Получаем исключенных игроков
    eliminated = Player.objects.filter(room=room, status='eliminated')
    
    context = {
        'session': session,
        'room': room,
        'survivors': survivors,
        'eliminated': eliminated,
        'result': session.result
    }
    
    return render(request, 'game/game_results.html', context)

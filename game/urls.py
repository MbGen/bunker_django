from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),
    
    # Аутентификация
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='game/auth/login.html',
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    
    # Страницы для создания и присоединения к игре
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('join/<str:room_id>/', views.join_game_by_id, name='join_game_by_id'),
    
    # Страницы игровой комнаты
    path('room/<str:room_id>/', views.game_room, name='game_room'),
    path('room/<str:room_id>/start/', views.start_game, name='start_game'),
    path('room/<str:room_id>/kick/<int:player_id>/', views.kick_player, name='kick_player'),
    
    # API для игровых действий
    path('api/ready/<int:player_id>/', views.set_player_ready, name='set_player_ready'),
    path('api/reveal/<int:player_id>/<str:attribute>/', views.reveal_attribute, name='reveal_attribute'),
    path('api/vote/<int:session_id>/<int:voter_id>/<int:target_id>/', views.vote_player, name='vote_player'),
    path('api/skip-elimination/<int:session_id>/', views.skip_elimination, name='skip_elimination'),
    path('api/use-card/<int:card_id>/<int:player_id>/', views.use_action_card, name='use_action_card'),
    path('api/next-player/<int:session_id>/', views.get_next_player, name='get_next_player'),
    
    # Страница результатов
    path('results/<int:session_id>/', views.game_results, name='game_results'),
]

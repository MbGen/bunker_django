"""
ASGI config for bunker_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

# Установка переменной окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_project.settings')

# Инициализация Django ASGI приложения (это должно быть до любых импортов моделей)
django_asgi_app = get_asgi_application()

# Теперь можно безопасно импортировать GameConsumer
from game.consumers import GameConsumer

# Определяем маршруты для WebSocket
websocket_urlpatterns = [
    path('ws/game/<str:room_id>/', GameConsumer.as_asgi()),
]

# Настраиваем приложение с поддержкой HTTP и WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,  # Обрабатывает HTTP-запросы
    "websocket": AllowedHostsOriginValidator(  # Обрабатывает WebSocket-запросы
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
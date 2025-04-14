# Веб-приложение "Бункер"

Многопользовательская онлайн-игра "Бункер", разработанная на Django.

## Описание

"Бункер" - это социальная игра, в которой игроки должны решить, кто из них достоин места в бункере во время катастрофы. Каждый игрок получает карточку персонажа с различными характеристиками (возраст, пол, профессия, здоровье, багаж, фобии и дополнительные факты). Игроки по очереди раскрывают информацию о своих персонажах и пытаются убедить других, что именно они должны выжить.

## Особенности

- Система комнат/лобби для создания и присоединения к играм
- Конфигурируемые параметры игры (катастрофы, профессии, состояния здоровья и т.д.)
- Система голосования для исключения игроков
- Чат для общения между игроками
- Карты действий для влияния на ход игры
- Административный интерфейс для управления игровыми данными

## Требования

- Python 3.8+
- Django 4.2+
- Channels для WebSocket
- PostgreSQL (рекомендуется) или SQLite
- Другие зависимости указаны в requirements.txt

## Установка

1. Клонируйте репозиторий:
```
git clone <url-репозитория>
cd bunker_game
```

2. Создайте виртуальное окружение и активируйте его:
```
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```
pip install -r requirements.txt
```

4. Настройте базу данных в settings.py (по умолчанию используется SQLite)

5. Примените миграции:
```
python manage.py migrate
```

6. Загрузите начальные данные:
```
python manage.py load_config
```

7. Создайте суперпользователя:
```
python manage.py createsuperuser
```

8. Запустите сервер:
```
python manage.py runserver
```

## Настройка игры

Все игровые параметры хранятся в JSON-файлах в директории `game/config/`:
- catastrophes.json - катастрофы
- professions.json - профессии
- health_states.json - состояния здоровья
- baggage.json - багаж
- phobias.json - фобии
- facts.json - факты о персонажах
- action_cards.json - карты действий

Вы можете редактировать эти файлы и затем обновить базу данных с помощью команды:
```
python manage.py load_config
```

## Развертывание в production

Для развертывания в production-среде рекомендуется:

1. Настроить HTTPS с помощью Nginx или Apache
2. Использовать Gunicorn или uWSGI в качестве WSGI-сервера
3. Настроить Daphne для обработки WebSocket-соединений
4. Использовать PostgreSQL в качестве базы данных
5. Настроить Redis для Channels

Пример конфигурации Nginx:
```
server {
    listen 80;
    server_name yourdomain.com;
    
    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/bunker_game;
    }
    
    location /media/ {
        root /path/to/bunker_game;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Лицензия

MIT

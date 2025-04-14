#!/bin/bash

# Скрипт для установки и запуска веб-приложения "Бункер"

echo "Установка веб-приложения 'Бункер'..."

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не найден. Пожалуйста, установите Python 3.8 или выше."
    exit 1
fi

# Проверка версии Python
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ $(echo "$python_version < 3.8" | bc) -eq 1 ]]; then
    echo "Требуется Python 3.8 или выше. Текущая версия: $python_version"
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt

# Применение миграций
echo "Применение миграций базы данных..."
python manage.py migrate

# Загрузка конфигурации
echo "Загрузка игровых данных..."
python manage.py load_config

# Создание суперпользователя
echo "Создание суперпользователя..."
echo "Вам будет предложено создать учетную запись администратора."
python manage.py createsuperuser

# Запуск сервера
echo "Запуск сервера разработки..."
echo "Приложение будет доступно по адресу http://127.0.0.1:8000/"
echo "Для остановки сервера нажмите Ctrl+C"
python manage.py runserver 0.0.0.0:8000

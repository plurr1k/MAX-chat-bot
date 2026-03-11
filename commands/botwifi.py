import asyncio
import logging
import random
import string
from maxapi import Bot, Dispatcher, types
import paramiko  # библиотека для SSH
import time  # <-- ВАЖНО: добавлен импорт time
import re  # <-- добавлен для работы с регулярными выражениями
import json  # <-- добавлен для работы с JSON
import os   # <-- для проверки существования файла
from config import dp
from datetime import datetime, timedelta  # <-- для работы с датами
from commands.user_subscribed import user_subscribed

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Конфигурация ---
BOT_TOKEN = 'f9LHodD0cOIZP9VjTzHgvRMVvy1qJihAvFnSn9SxD7upxy2YNyH13lPVriMi5zxt27ZHPgptUR8zyZzHzTYP'
MIKROTIK_IP = '192.168.1.46'  # IP вашего роутера
MIKROTIK_USER = 'admin'
MIKROTIK_PASSWORD = 'school617'
MIKROTIK_PORT = 22  # стандартный порт SSH
USER_PROFILE = 'student'  # профиль из предыдущих шагов
DATA_FILE = 'users_data.json'  # файл для хранения данных пользователей
ACCESS_VALID_DAYS = 7  # срок действия доступа в днях
# --------------------

existing_logins_cache = set()
cache_time = 0
CACHE_TTL = 30  # секунд

def generate_login(length=6):
    """Генерирует случайный логин из букв и цифр."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_password(length=8):
    """Генерирует случайный пароль."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_existing_logins():
    """Получает список всех существующих логинов из MikroTik."""
    global existing_logins_cache, cache_time
    
    # Обновляем кэш раз в 30 секунд
    current_time = time.time()
    if current_time - cache_time < CACHE_TTL and existing_logins_cache:
        return existing_logins_cache
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(MIKROTIK_IP, port=MIKROTIK_PORT,
                       username=MIKROTIK_USER, password=MIKROTIK_PASSWORD)
        
        command = '/ip hotspot user print terse'
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        client.close()
        
        # Парсим вывод для получения имен пользователей
        # Формат: ... name="username" ...
        logins = set(re.findall(r'name="([^"]+)"', output))
        
        existing_logins_cache = logins
        cache_time = current_time
        return logins
        
    except Exception as e:
        logging.error(f"Ошибка при получении списка логинов: {e}")
        return existing_logins_cache  # возвращаем старый кэш в случае ошибки

def add_user_to_mikrotik(login, password):
    """Подключается к MikroTik по SSH и добавляет пользователя."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(MIKROTIK_IP, port=MIKROTIK_PORT,
                       username=MIKROTIK_USER, password=MIKROTIK_PASSWORD)
        
        # Формирование команды MikroTik
        command = f'/ip hotspot user add name="{login}" password="{password}" profile={USER_PROFILE}'
        logging.info(f"Выполняю команду: {command}")
        
        stdin, stdout, stderr = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        
        stderr_output = stderr.read().decode().strip()
        client.close()
        
        if exit_status == 0:
            logging.info(f"Пользователь {login} успешно добавлен")
            return True, "OK"
        else:
            error_msg = stderr_output if stderr_output else f"Код ошибки: {exit_status}"
            logging.error(f"Ошибка добавления пользователя: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        logging.error(f"Ошибка подключения к MikroTik: {e}")
        return False, str(e)

@dp.message_created(types.Command('wifi'))
async def wifi_command(event: types.MessageCreated):
    if await user_subscribed(event) == False:
        return
    # Получаем список существующих логинов
    existing_logins = get_existing_logins()
    
    # Генерируем уникальный логин
    login = None
    max_attempts = 20
    
    for attempt in range(max_attempts):
        # Генерируем логин случайной длины от 6 до 8 символов
        length = random.choice([6, 7, 8])
        candidate = generate_login(length)
        
        if candidate not in existing_logins:
            login = candidate
            break
    
    if not login:
        await event.message.answer("❌ Система перегружена. Попробуйте позже.")
        return
    
    password = generate_password()
    
    logging.info(f"Генерирую доступ: логин={login}, пароль={password}")
    
    # Отправляем сообщение, что пароль генерируется
    await event.message.answer("⏳ Генерирую доступ в Wi-Fi...")
    
    # Добавляем пользователя в MikroTik
    success, message = add_user_to_mikrotik(login, password)
    
    if success:
        response = (f"✅ Доступ в Wi-Fi готов!\n\n"
                    f"📱 Логин: {login}\n"
                    f"🔑 Пароль: {password}\n\n"
                    f"Сессия действует 20 минут.")
        await event.message.answer(response)
    else:
        await event.message.answer("❌ Произошла ошибка при создании доступа. Попробуйте позже.")

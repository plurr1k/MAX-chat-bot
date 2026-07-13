# Get allow of wifi

import asyncio
import logging
import random
import string
import config
from maxapi import Bot, Dispatcher, types
import paramiko  # библиотека для SSH
import time  # <-- ВАЖНО: добавлен импорт time
import re  # <-- добавлен для работы с регулярными выражениями
import json  # <-- добавлен для работы с JSON
import os   # <-- для проверки существования файла
from config import dp, bot
from datetime import datetime, timedelta  # <-- для работы с датами
from commands.user_subscribed import user_subscribed

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Конфигурация ---
BOT_TOKEN = config.TOKEN # Токен бота
MIKROTIK_IPS = []  # IP ваших роутеров
MIKROTIK_USER = '' # Логин роутера
MIKROTIK_PASSWORD = '' # Пароль роутера
MIKROTIK_PORT = 22  # стандартный порт SSH
USER_PROFILE = 'student'  # профиль
DATA_FILE = 'jsons/users_wifi_data.json'  # файл для хранения данных пользователей
ACCESS_VALID_DAYS = 7  # срок действия доступа в днях
# --------------------

existing_logins_cache = set()
cache_time = 0
CACHE_TTL = 30  # секунд

def load_user_data():
    """Загружает данные пользователей  из файла."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    """Сохраняет данные пользователей в файл."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
    """Получает список всех существующих логинов из всех MikroTik роутеров."""
    global existing_logins_cache, cache_time
    
    # Обновляем кэш раз в 30 секунд
    current_time = time.time()
    if current_time - cache_time < CACHE_TTL and existing_logins_cache:
        return existing_logins_cache
    
    all_logins = set()
    for ip in MIKROTIK_IPS:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=MIKROTIK_PORT,
                           username=MIKROTIK_USER, password=MIKROTIK_PASSWORD)
            
            command = '/ip hotspot user print terse'
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode()
            client.close()
            
            # Парсим вывод для получения имен пользователей
            # Формат: ... name="username" ...
            logins = set(re.findall(r'name="([^"]+)"', output))
            all_logins.update(logins)
            
        except Exception as e:
            logging.error(f"Ошибка при получении списка логинов с {ip}: {e}")
            # Продолжаем с другими роутерами
    
    existing_logins_cache = all_logins
    cache_time = current_time
    return all_logins

def add_user_to_mikrotik(login, password):
    """Подключается к MikroTik по SSH и добавляет пользователя на все роутеры."""
    all_success = True
    errors = []
    for ip in MIKROTIK_IPS:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=MIKROTIK_PORT,
                           username=MIKROTIK_USER, password=MIKROTIK_PASSWORD)
            
            # Формирование команды MikroTik
            command = f'/ip hotspot user add name="{login}" password="{password}" profile={USER_PROFILE}'
            logging.info(f"Выполняю команду на {ip}: {command}")
            
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            stderr_output = stderr.read().decode().strip()
            client.close()
            
            if exit_status == 0:
                logging.info(f"Пользователь {login} успешно добавлен на {ip}")
            else:
                error_msg = stderr_output if stderr_output else f"Код ошибки: {exit_status}"
                logging.error(f"Ошибка добавления пользователя на {ip}: {error_msg}")
                all_success = False
                errors.append(f"{ip}: {error_msg}")
                
        except Exception as e:
            logging.error(f"Ошибка подключения к {ip}: {e}")
            all_success = False
            errors.append(f"{ip}: {str(e)}")
    
    if all_success:
        return True, "OK"
    else:
        return False, "; ".join(errors)

@dp.message_created(types.Command('wifi'))
async def wifi_command(event: types.MessageCreated):
    if await user_subscribed(event) == False:
        return
    user_id = event.message.sender.user_id
    
    # Загружаем данные пользователей
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    # Проверяем, есть ли активный доступ
    if user_id_str in user_data:
        last_timestamp = datetime.fromisoformat(user_data[user_id_str]['timestamp'])
        next_available = last_timestamp + timedelta(days=ACCESS_VALID_DAYS)
        if datetime.now() < next_available:
            response = (f"❌ У вас уже есть активный доступ к Wi-Fi.\n\n"
                        f"📌 Название: (sc617, sc617-cab223, sc617-cab108, sc617-cab115, sc617-cab116, sc617-cab227)\n"
                        f"🛜 Безопасность: WPA2 personal\n"
                        f"Сеть: скрытые.\n"
                        f"📱 Логин: {user_data[user_id_str]['login']}\n"
                        f"🔑 Пароль: {user_data[user_id_str]['password']}\n\n"
                        f"Следующий доступ можно получить после {next_available.strftime('%d.%m.%Y %H:%M')}.")
            await bot.send_message(user_id=user_id, text=response)
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
        # Сохраняем данные пользователя
        user_data[user_id_str] = {
            'login': login,
            'password': password,
            'timestamp': datetime.now().isoformat()
        }
        save_user_data(user_data)
        
        response = (f"✅ Доступ в Wi-Fi готов!\n\n"
                    f"📌 Название: (sc617, sc617-cab223, sc617-cab108, sc617-cab115, sc617-cab116, sc617-cab227)\n"
                    f"🛜 Безопасность: WPA2 personal"
                    f"Сеть: скрытые."
                    f"📱 Логин: {login}\n"
                    f"🔑 Пароль: {password}\n\n"
                    f"Сессия действует {ACCESS_VALID_DAYS} дней.")
        await bot.send_message(user_id=user_id, text=response)
    else:
        await event.message.edit("❌ Произошла ошибка при создании доступа. Попробуйте позже.")
# by plurr1k.
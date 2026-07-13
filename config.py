# Config
from maxapi import Bot, Dispatcher

TOKEN = '' # Токен бота

bot = Bot(TOKEN)  
dp = Dispatcher()

ADMINS_ID = [] # Айди админов
MAIN_CHAT_ID = None # Основной чат
ALL_CHATS = None # Список всех чатов
TRUST_DAYS = 7 # Количество дней, в течение которых участник считается "доверенным" после вступления в чат

# by plurr1k.
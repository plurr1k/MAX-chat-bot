from maxapi import Bot, Dispatcher

bot = Bot('f9LHodD0cOIZP9VjTzHgvRMVvy1qJihAvFnSn9SxD7upxy2YNyH13lPVriMi5zxt27ZHPgptUR8zyZzHzTYP')  # Токен бота
dp = Dispatcher()

ADMINS_ID = [184509708, 5277085] # Айди админов
MAIN_CHAT_ID = None # Основной чат
ALL_CHATS = None # Список всех чатов
TRUST_DAYS = 7 # Количество дней, в течение которых участник считается "доверенным" после вступления в чат
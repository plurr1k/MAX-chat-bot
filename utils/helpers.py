# All other functions

from config import bot
import config
from logger_config import logger
from maxapi.types import MessageCreated, MessageCallback
from maxapi.enums import chat_type
from datetime import datetime

# Функции безопасного получения атрибутов 
def safe_get_attr(obj, *attrs, default=None):
    """Безопасное получение атрибута"""
    for attr in attrs:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if value is not None:
                return value
    return default

async def get_bot_info_safe():
    """Безопасное получение информации о боте"""
    try:
        bot_info = await bot.get_me()
        return {
            'id': safe_get_attr(bot_info, 'id', default='неизвестно'),
            'first_name': safe_get_attr(bot_info, 'first_name', 'firstName', default='Бот'),
            'last_name': safe_get_attr(bot_info, 'last_name', 'lastName', default=''),
            'username': safe_get_attr(bot_info, 'username', 'user_name', default='неизвестно'),
            'is_bot': True,
            'is_premium': safe_get_attr(bot_info, 'is_premium', 'premium', default=False),
            'added_to_attachment_menu': safe_get_attr(bot_info, 'added_to_attachment_menu', 'attachment_menu', default=False)
        }
    except Exception as e:
        logger.error(f"Ошибка получения информации о боте: {e}")
        return {'first_name': 'Бот', 'username': 'неизвестно', 'id': 'неизвестно', 'is_bot': True}

async def get_user_info_safe(user_obj):
    """Безопасное получение полной информации о пользователе согласно документации"""
    if not user_obj:
        return {
            'id': None,
            'first_name': '',
            'last_name': '',
            'username': '',
            'is_bot': False,
            'is_premium': False,
            'added_to_attachment_menu': False,
            'full_name': '',
            'mention': ''
        }
    
    # Получаем все поля согласно документации
    info = {
        'id': safe_get_attr(user_obj, 'id', 'user_id', 'userId', default=None),
        'first_name': safe_get_attr(user_obj, 'first_name', 'firstName', 'name', default=''),
        'last_name': safe_get_attr(user_obj, 'last_name', 'lastName', 'surname', default=''),
        'username': safe_get_attr(user_obj, 'username', 'user_name', default=''),
        'is_bot': safe_get_attr(user_obj, 'is_bot', 'isBot', 'bot', default=False),
        'is_premium': safe_get_attr(user_obj, 'is_premium', 'premium', default=False),
        'added_to_attachment_menu': safe_get_attr(user_obj, 'added_to_attachment_menu', 'attachment_menu', default=False)
    }
    
    # Дополнительные поля
    full_name = info['first_name']
    if info['last_name']:
        full_name += f" {info['last_name']}"
    info['full_name'] = full_name.strip()
    if info['username']:
        info['mention'] = f"@{info['username']}"
    elif info['full_name']:
        info['mention'] = info['full_name']
    else:
        info['mention'] = f"Пользователь #{info['id']}" if info['id'] else "Неизвестный пользователь"
    
    return info

async def get_chat_info_safe(chat_obj):
    """Безопасное получение информации о чате"""
    if not chat_obj:
        return {}
    
    return {
        'title': safe_get_attr(chat_obj, 'title', 'name', 'chat_title'),
        'chat_id': safe_get_attr(chat_obj, 'chat_id', 'chatId', 'id'),
        'type': safe_get_attr(chat_obj, 'type', 'chat_type'),
        'participants_count': safe_get_attr(chat_obj, 'participants_count', 'member_count', 'members_count'),
        'participants': safe_get_attr(chat_obj, 'participants', 'members', default={}),
        'owner_id': safe_get_attr(chat_obj, 'owner_id', 'owner')
    }

async def get_chat_members_from_event(event: MessageCreated | int | MessageCallback):
    """Получить всех участников чата с пагинацией"""
    try:
        # Определяем chat_id
        if isinstance(event, int):
            chat_id = event

        elif isinstance(event, MessageCreated):
            chat_id = event.message.recipient.chat_id

        elif isinstance(event, MessageCallback):
            chat_id = event.message.recipient.chat_id


        all_members = []
        marker = None

        while True:
            response = await bot.get_chat_members(chat_id=chat_id, count=100, marker=marker )
            members = response.members
            all_members.extend(members)
            marker = getattr(response, "marker", None)
            if not marker:
                break

        return all_members

    except Exception as e:
        print(f"Ошибка получения участников: {e}")
        return []
    
async def get_chat_user_join_time(chat_info, user_info):
    """Информация о времени вступления в чат"""
    if chat_info['type'] == chat_type.ChatType.CHAT:
        member = await bot.get_chat_member(chat_id=chat_info['chat_id'], user_id=user_info['id'])
        if member.join_time != '':
            dt = datetime.fromtimestamp(member.join_time / 1000)
            formated_join_time = dt.strftime("%d.%m.%Y")
            return formated_join_time
        else:
            return "неизвестно"

async def get_chat_title_by_id(chat_id: int):
    """Получение названия чата по его id."""

    if not chat_id:
        return "Неизвестно"

    try:
        chat = await bot.get_chat_by_id(chat_id)
        info = await get_chat_info_safe(chat)
        return info.get("title", "Без названия")
    except Exception as e:
        logger.error(f"Ошибка получения чата {chat_id}: {e}")
        return "Неизвестно"
        
async def check_user_trust(chat_id: int, user_id: int) -> dict:
    """
    Проверяет доверенность пользователя:
    был ли он в чате больше TRUST_DAYS
    """

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)

        if not member.join_time:
            return {"trusted": False, "days": 0}

        join_dt = datetime.fromtimestamp(member.join_time / 1000)
        now = datetime.now()

        days_in_chat = (now - join_dt).days

        return {
            "trusted": days_in_chat >= config.TRUST_DAYS,
            "days": days_in_chat
        }

    except Exception as e:
        logger.error(f"Ошибка проверки доверенности: {e}")
        return {"trusted": False, "days": 0}
    
# by plurr1k.
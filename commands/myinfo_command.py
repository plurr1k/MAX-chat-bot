from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
from utils.helpers import get_user_info_safe, get_chat_title_by_id, get_chat_info_safe, get_chat_user_join_time
import config
from datetime import datetime
from logger_config import logger
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('myinfo'))
async def myinfo_command(event: MessageCreated):
    if await user_subscribed(event) == False:
        return
    """Полная информация о текущем пользователе"""
    try:
        user_info = await get_user_info_safe(event.message.sender)
        response = f"👤 *ВАША ПОЛНАЯ ИНФОРМАЦИЯ*\n\n"
        if user_info['full_name']:
            response += f"👤 *Вы:* {user_info['full_name']}\n"
        if user_info['username']:
            response += f"📱 *Username:* @{user_info['username']}\n"
        if user_info['id']:
            response += f"🆔 *Ваш ID:* `{user_info['id']}`\n"
        response += f"*Тип:* {'🤖 Бот' if user_info['is_bot'] else '👤 Пользователь'}\n"

        '''Информация о времени вступления в чат'''
        chat_id = event.message.recipient.chat_id
        chat = await bot.get_chat_by_id(chat_id)
        chat_info = await get_chat_info_safe(chat)
        
        # Информация о времени вступления в чат
        join_time = await get_chat_user_join_time(chat_info, user_info)
        if join_time:
            now = datetime.now()
            days_in_chat = (now - datetime.strptime(join_time, "%d.%m.%Y")).days
            response += f"📅 *В чате с:* {join_time} ({days_in_chat} дн.)\n"
            if days_in_chat >= config.TRUST_DAYS:
                response += f"✅ *Статус:* Доверенный"
            else:
                response += f"❌ *Статус:* Недоверенный"
        response += f"\n🎯 *Основной чат:* {await get_chat_title_by_id(config.MAIN_CHAT_ID)}\n"
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Ошибка в /myinfo: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")


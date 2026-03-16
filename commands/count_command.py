from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import chat_type, parse_mode
from utils.helpers import get_chat_info_safe, get_chat_members_from_event, get_chat_title_by_id
import config
from logger_config import logger
from datetime import datetime
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('count'))
async def count_command(event: MessageCreated):
    """Показать количество участников чата и статистику"""
    if await user_subscribed(event) == False:
        return
    try:
        chat_id = event.message.recipient.chat_id
        chat = await bot.get_chat_by_id(chat_id)
        chat_info = await get_chat_info_safe(chat)

        if chat_info['type'] == chat_type.ChatType.DIALOG:
            if config.MAIN_CHAT_ID is None:
                await event.message.answer("❌Основной чат для выполнения команды не установлен.")
                return
            members = await get_chat_members_from_event(config.MAIN_CHAT_ID)
        else:
            members = await get_chat_members_from_event(event)

        total = len(members)
        bots = 0
        users = 0

        for member in members:
            if getattr(member, 'is_bot', False):
                bots += 1
            else:
                users += 1

        response = f"📊 *СТАТИСТИКА ЧАТА*\n\n"
        if chat_info['type'] == chat_type.ChatType.DIALOG:
            response += f"📌 *Название:* {await get_chat_title_by_id(config.MAIN_CHAT_ID)}\n"
        else:
            response += f"📌 *Название:* {await get_chat_title_by_id(chat_id)}\n"
        response += f"👥 *Всего участников:* {total}\n"
        response += f"🤖 *Ботов:* {bots}\n"
        response += f"👤 *Пользователей:* {users}\n"
        response += f"\n⏰ *Время запроса:* {datetime.now().strftime('%H:%M:%S')}"
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /count: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")


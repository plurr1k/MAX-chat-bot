from config import bot, dp
import config
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.methods.get_chats import GetChats
from maxapi.enums import parse_mode
from utils.helpers import get_chat_info_safe
from logger_config import logger

@dp.message_created(types.Command('chats'))
async def get_all_bot_chats(event: MessageCreated, answer: bool = True):
    """Получить список всех чатов, в которых состоит бот (с пагинацией)"""
    try:
        if event.message.sender.user_id not in config.ADMINS_ID and answer == True:
            return
        config.ALL_CHATS = []
        marker = None

        while True:
            method = GetChats(bot=bot, count=100, marker=marker)
            response = await method.fetch()

            chats = getattr(response, "chats", []) or []
            config.ALL_CHATS.extend(chats)

            marker = getattr(response, "marker", None)
            if not marker:
                break

        if answer:
            if not config.ALL_CHATS:
                await event.message.answer("❌ Бот не состоит ни в одном чате")
                return

            response_text = "📋 *СПИСОК ЧАТОВ, В КОТОРЫХ СОСТОИТ БОТ:*\n\n"

            for chat in config.ALL_CHATS:
                chat_info = await get_chat_info_safe(chat)
                response_text += (
                    f"• {chat_info.get('title', 'Без названия')} "
                    f"(ID: `{chat_info.get('chat_id', 'неизвестно')}`)\n"
                )

            await bot.send_message(
                user_id=event.message.sender.user_id,
                text = response_text,
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            await event.message.delete()
    except Exception as e:
        logger.error(f"Ошибка в /chats: {e}")


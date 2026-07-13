# Get chat info

from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import chat_type, parse_mode
from commands.user_subscribed import user_subscribed

from utils.helpers import get_chat_info_safe
from commands.get_all_bot_chats import get_all_bot_chats
import config
from logger_config import logger

@dp.message_created(types.Command("chatinfo"))
async def chatinfo_command(event: MessageCreated):
    """Информация о текущем чате либо о чате по ID"""
    if await user_subscribed(event) == False:
        return
    try:        
        text = event.message.body.text.strip()
        parts = text.split()
        if len(parts) == 1:
            chat_id = event.message.recipient.chat_id
            chat = await bot.get_chat_by_id(chat_id)
            chat_info = await get_chat_info_safe(chat)
        elif len(parts) == 2:
            chat_id = parts[1]

            try:
                chat_id = int(chat_id)
            except ValueError as e:
                logger.error(f"Ошибка в /chatinfo: {e}")
                await event.message.answer(
                    "❌ Неверный формат ID чата\n\n"
                    "*Пример:*\n"
                    "`/chatinfo 123456` - полная информация о чате с ID 123456"
                    "`/chatinfo` - полная информация о текущем чате",
                    parse_mode=parse_mode.ParseMode.MARKDOWN)
                return
        
            await get_all_bot_chats(event, False)

            for this_chat in config.ALL_CHATS:
                chat_info = await get_chat_info_safe(this_chat)
                if chat_info["chat_id"] == int(parts[1]):
                    in_all_chats = True
                    break
                else:
                    in_all_chats = False
                
            if not in_all_chats:
                await event.message.answer(
                    f"❌ Этого чата нет в списке бота",
                    parse_mode=parse_mode.ParseMode.MARKDOWN)
                return
            
        else:
            await event.message.answer(
                "❌ Слишком много параметров\n\n"
                "*Пример:*\n"
                "`/chatinfo 123456` - полная информация о чате с ID 123456"
                "`/chatinfo` - полная информация о текущем чате",
                parse_mode=parse_mode.ParseMode.MARKDOWN)
            return
        if len(parts) == 1:
            response = f"💬 *ИНФОРМАЦИЯ О ТЕКУЩЕМ ЧАТЕ*\n\n"
        else:
            response = f"💬 *ИНФОРМАЦИЯ О ЧАТЕ С ID {chat_id}*\n\n"
        if chat_info.get('title'):
            response += f"📌 *Название:* {chat_info['title']}\n"
        if chat_info.get('chat_id'):
            response += f"🆔 *ID чата:* `{chat_info['chat_id']}`\n"
        if chat_info.get('participants_count'):
            response += f"👥 *Количество участников:* {chat_info['participants_count']}\n"
        
        if chat_info.get('type'):
            match chat_info['type']:
                case chat_type.ChatType.CHANNEL:
                    type_chat = "Канал"
                case chat_type.ChatType.CHAT:
                    type_chat = "Общий чат (беседа)"
                case chat_type.ChatType.DIALOG:
                    type_chat = "Личный чат"
                case _:  
                    type_chat = "Неизвестно"
            response += f"📚 *Тип:* {type_chat}\n"
        
        if config.MAIN_CHAT_ID == chat_info.get('chat_id'):
            response += f"\n🎯 *Чат является основным:* ✅ Да\n"
        else:
            response += f"\n🎯 *Чат является основным:* ❌ Нет\n"
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка в /chatinfo: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")
# by plurr1k.


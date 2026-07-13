# Get chat id

from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
from utils.helpers import get_chat_info_safe
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('getid'))
async def getid_command(event: MessageCreated):
    """Получение ID текущего чата"""
    chat_id = event.message.recipient.chat_id
    chat = await bot.get_chat_by_id(chat_id)
    chat_info = await get_chat_info_safe(chat)
    if chat_info.get('chat_id'):
        response = f"🆔 *ID этого чата:* `{chat_info['chat_id']}`\n"
    else:
        response = "🆔 *ID этого чата:* Недостуно\n"
    await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)

# by plurr1k
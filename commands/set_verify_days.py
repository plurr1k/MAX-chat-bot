# by plurr1k
from config import bot, dp
import config
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
from utils.helpers import get_chat_info_safe
from logger_config import logger
from datetime import datetime

@dp.message_created(types.Command('setverify'))
async def set_verify_days(event: MessageCreated):
    """Установить минимальное количество дней для доверенного пользователя"""

    chat_id = event.message.recipient.chat_id
    chat = await bot.get_chat_by_id(chat_id)
    chat_info = await get_chat_info_safe(chat)
    
    if event.message.sender.user_id not in config.ADMINS_ID:
        return

    parts = event.message.body.text.strip().split()

    if len(parts) != 2:
        await bot.send_message(user_id=event.message.sender.user_id,
            text ="❌ Укажите количество дней\n\n"
            "Пример:\n"
            "`/setverify 30`",
            parse_mode=parse_mode.ParseMode.MARKDOWN
        )
        return

    try:
        config.TRUST_DAYS = int(parts[1])
        await event.message.delete()
        await bot.send_message(user_id=event.message.sender.user_id,
            text=f"✅ Минимальный срок доверенности установлен: {config.TRUST_DAYS} дней"
        )
    except ValueError:
        await event.message.answer("❌ Значение должно быть числом")

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


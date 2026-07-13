# Check user subscribed

from maxapi.types import LinkButton, MessageCreated
from config import dp, bot
from commands.get_all_bot_chats import get_all_bot_chats
from logger_config import logger
import config
from utils.helpers import get_chat_info_safe, get_user_info_safe
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

#  Проверка на подписку
async def user_subscribed(event: MessageCreated) -> bool:
    try:
        # Пропускаем сообщения от ботов и админов
        if event.message.sender.is_bot:
            return True
        
        if event.message.sender.user_id in config.ADMINS_ID:
            return True
        
        user_id = event.message.sender.user_id
        user = event.message.sender
        user = await get_user_info_safe(user)
        channel_id = '-69338228951554'  
        await get_all_bot_chats(event, False)
        is_subscribed = False
        marker = None
        limit = 100

        while True:
            response = await bot.get_chat_members(
                chat_id=channel_id,
                count=limit,
                marker=marker
            )

            for member in response.members:
                if member.user_id == user_id:
                    return True

            if not response.marker:
                break

            marker = response.marker


        if not is_subscribed:
            builder = InlineKeyboardBuilder()
            builder.row(
                LinkButton(
                    text="Подписаться на канал",
                    url="https://max.ru/id7814103632_gos"
                )
            )
            await event.message.delete()
            await event.message.answer(
                text=f"❗ {user['full_name']}, для использования бота подпишитесь на канал",
                attachments=[builder.as_markup()]
            )
            return False


    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")


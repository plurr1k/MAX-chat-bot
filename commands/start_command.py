# Start bot command

from config import dp
from maxapi import F, types
from maxapi.types import MessageCreated
from utils.helpers import get_bot_info_safe
from logger_config import logger
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('start'))
async def start_command(event: types.MessageCreated):
    if await user_subscribed(event) == False:
        return
    """Обработчик команды /start"""
    try:
        bot_info = await get_bot_info_safe()
        
        response = (
            f"👋 Привет! Я {bot_info['first_name']} (@{bot_info['username']})\n\n"
            f"/help - Покажет все команды бота\n"
        )
        
        await event.message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await event.message.answer("❌ Ошибка при запуске")


# by plurr1k
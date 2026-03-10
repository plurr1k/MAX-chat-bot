from config import dp
from maxapi import F
from maxapi.types import MessageCreated
from utils.helpers import get_bot_info_safe
from logger_config import logger

@dp.message_created(F.message.body.text.startswith("/start"))
async def start_command(event: MessageCreated):
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



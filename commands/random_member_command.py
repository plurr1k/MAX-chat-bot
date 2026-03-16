from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import chat_type, parse_mode
from utils.helpers import get_chat_info_safe, get_chat_members_from_event, get_chat_title_by_id
import config
from logger_config import logger
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('random'))
async def random_member_command(event: MessageCreated):
    if await user_subscribed(event) == False:
        return
    """Выбор случайного участника чата (отправка кнопок)"""
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
        
        human_members = [m for m in members if not getattr(m, 'is_bot', False) and not getattr(m, 'is_admin', False)] # Исключаем ботов и админов

        if not human_members:
            await event.message.answer(
                "❌ В чате не найдено участников.\n"
                "Боты и админы исключены из случайного выбора."
            )
            return

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="1", payload="btn_rnd1"),
            CallbackButton(text="5", payload="btn_rnd5"),
            CallbackButton(text="10", payload="btn_rnd10")
        )

        await event.message.answer(
            "🎲 **СЛУЧАЙНЫЙ ВЫБОР** 🎲\nВыберите количество участников для случайного выбора\n",
            parse_mode=parse_mode.ParseMode.MARKDOWN,
            attachments=[builder.as_markup()]
        )

    except Exception as e:
        logger.error(f"Ошибка в /random: {e}")
        await event.message.answer("⚠️ Ошибка при выборе участника. Попробуйте еще раз.")



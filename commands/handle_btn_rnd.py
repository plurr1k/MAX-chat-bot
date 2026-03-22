# by plurr1k
from config import bot, dp
from maxapi import F
from maxapi.types import MessageCallback
from maxapi.enums import chat_type, parse_mode
from utils.helpers import get_chat_info_safe, get_chat_members_from_event, get_user_info_safe
import config
from logger_config import logger
import random

@dp.message_callback(F.callback.payload.startswith("btn_rnd"))
async def handle_btn_rnd(event: MessageCallback):
    """Ответ на нажатие callback-кнопки и выбор участников"""
    try:
        chat_id = event.message.recipient.chat_id
        chat = await bot.get_chat_by_id(chat_id)
        chat_info = await get_chat_info_safe(chat)

        if chat_info['type'] == chat_type.ChatType.DIALOG:
            members = await get_chat_members_from_event(config.MAIN_CHAT_ID)
        else:
            members = await get_chat_members_from_event(event)

        human_members = [m for m in members if not getattr(m, 'is_bot', False)] # Исключаем ботов

        if not human_members:
            await event.message.answer(
                "❌ В чате не найдено участников.\n"
                "Боты исключены из случайного выбора."
            )
            return

        random_members_count = int(event.callback.payload.replace("btn_rnd", ""))
        if len(human_members) < random_members_count:
            await event.message.edit("❌ В чате не достаточно участников для этого случайного выбора.\n")
            return

        if random_members_count > 1:
            response = f"🎲 **СЛУЧАЙНЫЙ ВЫБОР УЧАСТНИКОВ**\n"
        else:
            response = f"🎲 **СЛУЧАЙНЫЙ ВЫБОР УЧАСТНИКА**\n"

        selected_members = []
        for member_number in range(random_members_count):
            while True:
                selected = random.choice(human_members)
                if selected not in selected_members:
                    selected_members.append(selected)
                    break
                else:
                    logger.warning(f"Повторный выбор участника {selected}, выбираю снова...")

            user_info = await get_user_info_safe(selected)
            response += f"\n📌 **Участник #{member_number+1}**"
            response += f"\n👉 **Выбран:** {user_info['full_name']}\n"
            response += f"🆔 **ID:** `{user_info['id']}`\n"
            if user_info['username']:
                response += f"📛 **Username:** @{user_info['username']}\n"

        response += f"\n👥 **Всего участников в чате:** {len(human_members)}"
        await event.message.edit(response, parse_mode=parse_mode.ParseMode.MARKDOWN, attachments=[] )
        logger.info(f"Выбран случайный участник: {user_info['full_name']} (ID: {user_info['id']})")

    except Exception as e:
        logger.error(f"Ошибка при обработке callback btn_rnd: {e}")
        await event.message.edit("⚠️ Ошибка при выборе участника. Попробуйте еще раз.", attachments=[])




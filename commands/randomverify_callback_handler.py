from config import bot, dp
import config
from maxapi.types import MessageCallback
from maxapi.enums import parse_mode
from utils.helpers import get_chat_members_from_event, get_user_info_safe, check_user_trust, get_chat_title_by_id
import json, random, datetime
from logger_config import logger
from datetime import timezone, datetime

@dp.message_callback()
async def randomverify_callback_handler(event: MessageCallback):
    """
    Обработка нажатия кнопки выбора количества участников
    """
    try:
        if event.callback.user.user_id not in config.ADMINS_ID:
            return
        await event.message.edit("🔄  Выбираю..", attachments=[])
        data = json.loads(event.callback.payload)
        chat1_id = data["chat1"]
        chat2_id = data["chat2"]
        count = data["count"]

        # --- Получаем пересечение участников ---
        members_chat1 = [
            m for m in await get_chat_members_from_event(chat1_id)
            if not getattr(m, "is_bot", False) and not getattr(m, "is_admin", False)
        ]
        members_chat2 = [
            m for m in await get_chat_members_from_event(chat2_id)
            if not getattr(m, "is_bot", False) and not getattr(m, "is_admin", False)
        ]

        ids_chat1 = {getattr(m, "user_id", None) for m in members_chat1 if getattr(m, "user_id", None)}
        ids_chat2 = {getattr(m, "user_id", None) for m in members_chat2 if getattr(m, "user_id", None)}
        intersection_ids = list(ids_chat1.intersection(ids_chat2))

        if not intersection_ids:
            await event.message.edit("❌ Нет общих пользователей между чатами")
            return

        # --- Фильтруем доверенных участников ---
        trusted_users = []
        for user_id in intersection_ids:
            trust1 = await check_user_trust(chat1_id, user_id)
            trust2 = await check_user_trust(chat2_id, user_id)
            if trust1["trusted"] and trust2["trusted"]:
                trusted_users.append(user_id)

        if len(trusted_users) < count:
            await event.message.edit(f"❌ Недостаточно доверенных участников (требуется {count})")
            return

        # --- Выбор случайных участников ---
        selected_ids = random.sample(trusted_users, count)

        # --- Составление ответа ---
        response = f"🎲 *СЛУЧАЙНЫЕ ДОВЕРЕННЫЕ УЧАСТНИКИ*\n"
        for idx, user_id in enumerate(selected_ids, start=1):
            member_chat1 = await bot.get_chat_member(chat1_id, user_id)
            member_chat2 = await bot.get_chat_member(chat2_id, user_id)
            user_info = await get_user_info_safe(member_chat1)
            response += f"\n📌 **Участник #{idx}**\n"
            response += f"*ФИО:* {user_info['full_name']}\n"
            response += f"*ID:* {user_info['id']}\n"
            if user_info.get("username"):
                response += f" 📱 *Username:* @{user_info['username']}\n"

            # Дата вступления и дни в каждом чате
            now = datetime.now(timezone.utc)
            for chat_idx, member in enumerate([member_chat1, member_chat2], start=1):
                join_date = getattr(member, "join_time", None)
                if join_date is not None:
                    dt_from_ms = datetime.fromtimestamp(join_date / 1000, tz=timezone.utc)
                    chat_name = ""
                    if chat_idx == 1:
                        chat_name = await get_chat_title_by_id(chat1_id)
                    else:
                        chat_name = await get_chat_title_by_id(chat2_id)
                    days_in_chat = (now - dt_from_ms).days
                    response += f"✅ Чат {chat_name} вступил: {dt_from_ms.strftime('%d.%m.%Y')}"
                    response += f"\nВ чате: {days_in_chat} дней\n"

        await event.message.edit(response, parse_mode=parse_mode.ParseMode.MARKDOWN, attachments=[])

    except Exception as e:
        await event.message.edit(f"💥 Ошибка при выборе участников:\n`{str(e)[:300]}`")
        logger.error(f"CRITICAL /randomverify callback error: {e}")
    
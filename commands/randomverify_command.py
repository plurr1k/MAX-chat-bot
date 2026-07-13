# Random verified member
from config import bot, dp
import config
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
from utils.helpers import get_chat_info_safe, get_chat_members_from_event
from commands.get_all_bot_chats import get_all_bot_chats
from datetime import datetime, timedelta, timezone
import json, os
from logger_config import logger
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from commands.user_subscribed import user_subscribed
from maxapi.types.attachments.buttons import CallbackButton

@dp.message_created(types.Command('randomverify'))
async def randomverify_command(event: MessageCreated):
    """
    /randomverify CHAT_ID_1 CHAT_ID_2
    После запуска показывает кнопки для выбора количества участников (1, 5, 10)
    """
    if await user_subscribed(event) == False:
        return
    try:
        parts = event.message.body.text.strip().split()
        if len(parts) != 3:
            await event.message.answer(
                "❌ Укажите 2 ID чатов\nПример:\n`/randomverify -12345 -67890`",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return

        try:
            chat1_id = int(parts[1])
            chat2_id = int(parts[2])
        except ValueError:
            await event.message.answer("❌ ID чатов должны быть числами")
            return

        # --- Получаем список всех чатов бота ---
        await get_all_bot_chats(event, False)
        bot_chat_ids = [
            info.get("chat_id") 
            for chat in config.ALL_CHATS or [] 
            if (info := await get_chat_info_safe(chat)).get("chat_id")
        ]
        if chat1_id not in bot_chat_ids or chat2_id not in bot_chat_ids:
            await event.message.answer(
                "❌ Один или оба чата отсутствуют в списке бота.\nИспользуйте `/chats` для просмотра доступных.",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        
        chat_info1 = await bot.get_chat_by_id(chat1_id)
        chat_info2 = await bot.get_chat_by_id(chat2_id)
        owner_id1 = chat_info1.owner_id
        owner_id2 = chat_info2.owner_id
        owner_info1 = await bot.get_chat_member(chat1_id, owner_id1)
        owner_info2 = await bot.get_chat_member(chat2_id, owner_id2)
        create_time1 = datetime.fromtimestamp(owner_info1.join_time / 1000, tz=timezone.utc)
        create_time2 = datetime.fromtimestamp(owner_info2.join_time / 1000, tz=timezone.utc)
        now_time = datetime.now(timezone.utc)
        
        if (create_time1 > create_time2):
            create_time1, create_time2 = create_time2, create_time1

        if (now_time - create_time1) < timedelta(days=config.TRUST_DAYS):
            days_after_create = now_time - create_time1
            await event.message.answer(f"❌ Количество дней для доверенного пользователя превышеает количество дней создание чата 1 \n"+
                  f"Количество дней доверенного пользователя не должно превышать {days_after_create.days} дней")
            return
        if (now_time - create_time2) < timedelta(days=config.TRUST_DAYS):
            days_after_create = now_time - create_time2
            await event.message.answer(f"❌ Количество дней для доверенного пользователя превышеает количество дней создание чата 2 \n"+
                  f"Количество дней доверенного пользователя не должно превышать {days_after_create.days} дней")
            return

        # --- Получаем участников обоих чатов ---
        members_chat1 = [
            m for m in await get_chat_members_from_event(chat1_id)
            if not getattr(m, "is_bot", False) and not getattr(m, "is_admin", False)
        ]
        members_chat2 = [
            m for m in await get_chat_members_from_event(chat2_id)
            if not getattr(m, "is_bot", False) and not getattr(m, "is_admin", False)
        ]

        if not members_chat1 or not members_chat2:
            await event.message.answer("❌ В одном из чатов нет подходящих участников.")
            return

        ids_chat1 = {getattr(m, "user_id", None) for m in members_chat1 if getattr(m, "user_id", None)}
        ids_chat2 = {getattr(m, "user_id", None) for m in members_chat2 if getattr(m, "user_id", None)}
        intersection_ids = list(ids_chat1.intersection(ids_chat2))

        if not intersection_ids:
            await event.message.answer("❌ Нет общих пользователей между чатами")
            return

        # --- Сохраняем JSON ---
        os.makedirs("jsons", exist_ok=True)
        for chat_id, ids in [(chat1_id, ids_chat1), (chat2_id, ids_chat2)]:
            with open(f"jsons/chat_{chat_id}_users.json", "w", encoding="utf-8") as f:
                json.dump(list(ids), f, ensure_ascii=False, indent=4)
        with open(f"jsons/intersection_{chat1_id}_{chat2_id}.json", "w", encoding="utf-8") as f:
            json.dump(intersection_ids, f, ensure_ascii=False, indent=4)

        # --- Отправка кнопок для выбора количества участников ---
        builder = InlineKeyboardBuilder()
        for count in [1, 5, 10]:
            builder.add(
                CallbackButton(
                    text=f"{count}",
                    payload=json.dumps({"chat1": chat1_id, "chat2": chat2_id, "count": count})
                )
            )
        await event.message.answer(
            "Выберите количество случайных доверенных участников:", 
            attachments=[builder.as_markup()]
        )

    except Exception as e:
        await event.message.answer(f"💥 Критическая ошибка:\n`{str(e)[:300]}`")
        logger.error(f"CRITICAL /randomverify error: {e}")

# by plurr1k
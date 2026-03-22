# by plurr1k
from maxapi.types import MessageCreated
from maxapi import types
from maxapi.enums import parse_mode
from utils.helpers import get_user_info_safe, get_chat_info_safe, get_chat_members_from_event, get_chat_user_join_time
from commands.get_all_bot_chats import get_all_bot_chats
from datetime import datetime
from logger_config import logger
from config import dp, bot
from commands.user_subscribed import user_subscribed
import pandas as pd

@dp.message_created(types.Command('abitur'))
async def user_full_info_command(event: MessageCreated):
    """Информация о поступающем"""
    if await user_subscribed(event) == False:
        return
    try:
        chat_id = event.message.recipient.chat_id
        chat = await bot.get_chat_by_id(chat_id)
        chat_info = await get_chat_info_safe(chat)

        text = event.message.body.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            await event.message.answer(
                "❌ Укажите ID поступающего\n\n"
                "*Пример:*\n"
                "`/abitur 123456` - полная информация о поступающем с ID 123456",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        try:
            target_code = int(parts[1])
        except:
            await event.message.answer(
            "❌ ID поступающего должен быть цифрами\n\n"
            "*Пример:*\n"
            "`/abitur 123456` - полная информация о поступающем с ID 123456",
            parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return

        res = await event.message.answer("🔄  Ищу участника..")

        df = pd.read_excel('jsons/Бот_Умные дети_2026.xlsx', engine='openpyxl')

        result = df[df['Код'] == int(target_code)]
        print(result)
        print(df)
        if not result.empty:
            row = result.iloc[0]
            response = (f"✅ Найден участник:\n"
            f"👤 ФИО: {row['Фамилия']} {row['Имя']} {row['Отчество']}\n"
            f"📚 Баллы: {row['Баллы']}\n"
            f"✏ Статус: {row['Статус']}\n")
            await res.message.edit(response)
        else:
            await res.message.edit(f"❌ Участник с кодом {target_code} не найден.")

    except Exception as e:
        logger.error(f"Ошибка в /abitur: {e}")   
# by plurr1k.
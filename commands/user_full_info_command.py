# Full info about user

from config import bot, dp
import config
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
from utils.helpers import get_user_info_safe, get_chat_info_safe, get_chat_members_from_event, get_chat_user_join_time
from commands.get_all_bot_chats import get_all_bot_chats
from datetime import datetime
from logger_config import logger
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('userinfo'))
async def user_full_info_command(event: MessageCreated):
    """Полная информация о пользователе со всеми полями"""
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
                "❌ Укажите ID пользователя\n\n"
                "*Пример:*\n"
                "`/userinfo 123456` - полная информация о пользователе с ID 123456",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        
        identifier = parts[1]
        is_username = False
        if identifier.startswith("@"):
            identifier = identifier[1:]
            is_username = True
        answer_message = await event.message.answer(f"🔍 Получаю полную информацию о пользователе: {identifier}")
        
        # Определяем USER_ID и ищем пользователя во всех чатах бота
        user_id = None
        if not is_username:
            if identifier.isdigit():
                user_id = int(identifier)
            else:
                await event.message.answer("❌ ID должен быть числом")
                return

        user_info = None
        # обновляем список чатах бота
        await get_all_bot_chats(event, False)
        search_chats = config.ALL_CHATS

        for chat in search_chats:
            try:
                tmp_info = await get_chat_info_safe(chat)
                members = await get_chat_members_from_event(tmp_info['chat_id'])
                chat_info = tmp_info
            except Exception:
                continue

            for member in members:
                if is_username:
                    if hasattr(member, 'username') and member.username == identifier:
                        user_id = getattr(member, 'user_id', None) or getattr(member, 'id', None)
                        user_info = await get_user_info_safe(member)
                        break
                else:
                    if hasattr(member, 'user_id') and member.user_id == user_id:
                        user_info = await get_user_info_safe(member)
                        break
            if user_info:
                break

        if user_info is None:
            await event.message.answer(
                f"❌ Пользователь с {'username' if is_username else 'ID'} `{identifier}` не найден ни в одном чате бота",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return

        if user_id == None: 
            await event.message.answer(f"❌ Пользователь с ID \ username `{identifier}` не найден в этом чате", parse_mode=parse_mode.ParseMode.MARKDOWN)
            return
        
        response = f"👤 *ПОЛНАЯ ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ С ID {user_info['id']}*\n\n"
        if user_info['full_name']:
            response += f"👤 *ФИО:* {user_info['full_name']}\n"
        if user_info['username']:
            response += f"📱 *Username:* @{user_info['username']}\n"
        if user_info['id']:
            response += f"🆔 *ID:* `{user_info['id']}`\n"
        response += f"*Тип:* {'🤖 Бот' if user_info['is_bot'] else '👤 Пользователь'}\n"
        join_time = await get_chat_user_join_time(chat_info, user_info)
        if join_time:
            now = datetime.now()
            days_in_chat = (now - datetime.strptime(join_time, "%d.%m.%Y")).days
            response += f"📅 *В чате с:* {join_time} ({days_in_chat} дн.)\n"
            if days_in_chat >= config.TRUST_DAYS:
                response += f"✅ *Статус:* Доверенный"
            else:
                response += f"❌ *Статус:* Недоверенный"
        await answer_message.message.edit(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /userinfo: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

# by plurr1k


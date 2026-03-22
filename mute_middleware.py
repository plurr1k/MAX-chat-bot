# by plurr1k
from maxapi.filters.middleware import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict
from datetime import datetime
import asyncio

from maxapi.types import MessageCreated
from maxapi.enums import parse_mode, chat_type

from config import bot
import config
from logger_config import logger
from utils.helpers import get_chat_info_safe
from mute_command import mute_manager


class AntiSpamMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: Dict[str, Any],
    ) -> Any:

        # Обрабатываем только сообщения
        if not isinstance(event_object, MessageCreated):
            return await handler(event_object, data)

        message = event_object.message
        user_id = event_object.message.sender.user_id
        user_name = event_object.message.sender.full_name
        chat_id = event_object.message.recipient.chat_id

        # Пропускаем ботов и админов
        if message.sender.is_bot or user_id in config.ADMINS_ID:
            return await handler(event_object, data)

        # Получаем информацию о чате
        try:
            chat = await bot.get_chat_by_id(chat_id)
            chat_info = await get_chat_info_safe(chat)
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о чате: {e}")
            return await handler(event_object, data)

        if chat_info.get("type") == chat_type.ChatType.DIALOG:
            return await handler(event_object, data)

        chat_title = chat_info.get("title", "Неизвестный чат")
        current_time = datetime.now()

        text = ""
        if message.body and hasattr(message.body, "text"):
            text = message.body.text

        # ====================
        # Проверка мута
        # ====================
        if mute_manager.is_muted(chat_id, user_id, current_time):
            try:
                await message.delete()
            except Exception:
                pass
            return  # пропускаем дальше

        # ====================
        # Спам командами
        # ====================
        if text.startswith("/") and mute_manager.check_command_spam(chat_id, user_id, current_time):
            mute_info = mute_manager.mute_user(chat_id, user_id, user_name, chat_title, current_time)
            await self._handle_mute(message, chat_id, user_id, user_name, chat_title, mute_info)
            return

        # ====================
        # Флуд
        # ====================
        if mute_manager.check_flood(chat_id, user_id, current_time):
            mute_info = mute_manager.mute_user(chat_id, user_id, user_name, chat_title, current_time)
            await self._handle_mute(message, chat_id, user_id, user_name, chat_title, mute_info)
            return

        # Передаем управление следующему обработчику
        return await handler(event_object, data)

    async def _handle_mute(self, message, chat_id, user_id, user_name, chat_title, mute_info):
        """Удаление сообщения, уведомление в чат и ЛС"""

        try:
            await message.delete()
        except Exception:
            pass

        mute_end_str = mute_info["mute_end"].strftime("%d.%m.%Y %H:%M:%S")
        duration_str = "24 часа" if mute_info["duration"].days > 0 else "30 минут"

        # ЛС пользователю
        private_msg = (
            f"🚫 **ВЫ ПОЛУЧИЛИ МУТ**\n\n"
            f"Чат: {chat_title}\n"
            f"Причина: {mute_info['reason']}\n"
            f"Длительность: {duration_str}\n"
            f"Окончание: {mute_end_str}\n"
            f"Нарушений за 24 часа: {mute_info['mute_count']}/3"
        )

        try:
            await bot.send_message(user_id=user_id, text=private_msg, parse_mode=parse_mode.ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Не удалось отправить ЛС пользователю {user_id}: {e}")

        # Сообщение в чат
        try:
            notif = await bot.send_message(chat_id=chat_id, text=f"⚠️ {user_name} получил мут на {duration_str}")
            asyncio.create_task(self._delete_notification(chat_id, notif))
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление в чат: {e}")

    async def _delete_notification(self, chat_id, notification):
        """Удаление уведомления через 10 секунд"""
        await asyncio.sleep(10)
        message_id = getattr(notification, "message_id", None) or getattr(notification, "id", None)
        if not message_id and isinstance(notification, dict):
            message_id = notification.get("message_id") or notification.get("id")
        if not message_id:
            return
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
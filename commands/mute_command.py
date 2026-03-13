from collections import defaultdict
from datetime import datetime, timedelta
from logger_config import logger
import asyncio
from config import dp, bot
from utils.helpers import get_chat_info_safe
from maxapi.enums import parse_mode, chat_type
from maxapi.types import MessageCreated
import config
import json
from maxapi import F

# ========== КЛАСС ДЛЯ УПРАВЛЕНИЯ МУТАМИ ==========

class MuteManager:
    def __init__(self):
        self.data_file = "jsons/mute_data.json"
        self.user_messages = defaultdict(lambda: defaultdict(list))
        self.muted_users = defaultdict(dict)
        self.user_mute_history = defaultdict(dict)
        self.load_data()

    def load_data(self):
        """Загружает данные из JSON файла с преобразованием ключей в int"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Загрузка muted_users с преобразованием ключей
                muted_users_data = {}
                for chat_id_str, users in data.get('muted_users', {}).items():
                    chat_id = int(chat_id_str)
                    muted_users_data[chat_id] = {}
                    for user_id_str, info in users.items():
                        user_id = int(user_id_str)
                        if 'mute_end_time' in info:
                            info['mute_end_time'] = datetime.fromisoformat(info['mute_end_time'])
                        muted_users_data[chat_id][user_id] = info
                self.muted_users = defaultdict(dict, muted_users_data)
                
                # Загрузка user_mute_history с преобразованием ключей
                history_data = {}
                for user_id_str, hist in data.get('user_mute_history', {}).items():
                    user_id = int(user_id_str)
                    if 'first_mute_time' in hist:
                        hist['first_mute_time'] = datetime.fromisoformat(hist['first_mute_time'])
                    if 'last_mute_time' in hist:
                        hist['last_mute_time'] = datetime.fromisoformat(hist['last_mute_time'])
                    history_data[user_id] = hist
                self.user_mute_history = defaultdict(dict, history_data)
                
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Ошибка загрузки данных из JSON: {e}")

    def save_data(self):
        """Сохраняет данные в JSON файл"""
        try:
            data = {
                'muted_users': dict(self.muted_users),
                'user_mute_history': dict(self.user_mute_history)
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o), ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных в JSON: {e}")

    def check_flood(self, chat_id: int, user_id: int, current_time: datetime) -> bool:
        """Проверяет, является ли сообщение флудом (5+ сообщений за 5 секунд)"""
        self.user_messages[chat_id][user_id] = [
            t for t in self.user_messages[chat_id][user_id]
            if (current_time - t).total_seconds() <= 5
        ]
        self.user_messages[chat_id][user_id].append(current_time)
        return len(self.user_messages[chat_id][user_id]) >= 5
    
    def is_muted(self, chat_id: int, user_id: int, current_time: datetime) -> bool:
        """Проверяет, замучен ли пользователь в чате"""
        if user_id in self.muted_users[chat_id]:
            mute_end = self.muted_users[chat_id][user_id]['mute_end_time']
            if current_time < mute_end:
                return True
            else:
                del self.muted_users[chat_id][user_id]
        return False
    
    def mute_user(self, chat_id: int, user_id: int, user_name: str, chat_title: str, current_time: datetime) -> dict:
        """Мутит пользователя и возвращает информацию о муте"""
        if user_id in self.user_mute_history:
            first_mute = self.user_mute_history[user_id].get('first_mute_time')
            if first_mute and (current_time - first_mute).total_seconds() <= 24 * 3600:
                mute_count = self.user_mute_history[user_id].get('mute_count', 0) + 1
            else:
                mute_count = 1
                self.user_mute_history[user_id]['first_mute_time'] = current_time
        else:
            mute_count = 1
            self.user_mute_history[user_id]['first_mute_time'] = current_time
        
        if mute_count >= 3:
            mute_duration = timedelta(days=1)  # 24 часа
            mute_reason = "третье нарушение за 24 часа"
        else:
            mute_duration = timedelta(minutes=30)  # 30 минут
            mute_reason = "флуд"
        
        mute_end = current_time + mute_duration
        
        self.muted_users[chat_id][user_id] = {
            'mute_end_time': mute_end,
            'mute_count': mute_count
        }
        
        self.user_mute_history[user_id]['mute_count'] = mute_count
        self.user_mute_history[user_id]['last_mute_time'] = current_time
        
        self.save_data()
        return {
            'mute_end': mute_end,
            'duration': mute_duration,
            'reason': mute_reason,
            'mute_count': mute_count
        }
    
    def unmute_user(self, chat_id: int, user_id: int):
        """Размучивает пользователя в чате"""
        if user_id in self.muted_users[chat_id]:
            del self.muted_users[chat_id][user_id]
            self.save_data()
            return True
        return False
    
    def cleanup_old_data(self, current_time: datetime):
        """Очищает устаревшие данные"""
        for chat_id in list(self.user_messages.keys()):
            for user_id in list(self.user_messages[chat_id].keys()):
                self.user_messages[chat_id][user_id] = [
                    t for t in self.user_messages[chat_id][user_id]
                    if (current_time - t).total_seconds() <= 5
                ]
                if not self.user_messages[chat_id][user_id]:
                    del self.user_messages[chat_id][user_id]
        
        for chat_id in list(self.muted_users.keys()):
            for user_id in list(self.muted_users[chat_id].keys()):
                if current_time >= self.muted_users[chat_id][user_id]['mute_end_time']:
                    del self.muted_users[chat_id][user_id]
        
        for user_id in list(self.user_mute_history.keys()):
            if 'first_mute_time' in self.user_mute_history[user_id]:
                if (current_time - self.user_mute_history[user_id]['first_mute_time']).total_seconds() > 24 * 3600:
                    del self.user_mute_history[user_id]
        self.save_data()

# Создаем глобальный экземпляр менеджера мутов
mute_manager = MuteManager()

async def cleanup_task():
    """Задача для периодической очистки устаревших данных"""
    while True:
        try:
            current_time = datetime.now()
            mute_manager.cleanup_old_data(current_time)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки: {e}")
            await asyncio.sleep(60)

# ========== ОБРАБОТЧИК АНТИСПАМА ==========
@dp.message_created(F.message.body.text.startswith("/unmute"))
async def unmute(event: MessageCreated):
    """Размут пользователя"""


@dp.message_created()
async def anti_spam_handler(event: MessageCreated):
    """Проверяет сообщения на флуд и мутит нарушителей"""
    try:
        # Пропускаем сообщения от ботов и админов
        if event.message.sender.is_bot:
            return
        
        if event.message.sender.user_id in config.ADMINS_ID:
            return
        
        # Проверяем тип чата (не обрабатываем личные сообщения)
        chat_id = event.message.recipient.chat_id
        chat = await bot.get_chat_by_id(chat_id)
        chat_info = await get_chat_info_safe(chat)
        
        if chat_info['type'] == chat_type.ChatType.DIALOG:
            return
        
        user_id = event.message.sender.user_id
        user_name = event.message.sender.first_name
        chat_title = chat_info.get('title', 'Неизвестный чат')
        current_time = datetime.now()
        
        # Проверяем, не замучен ли пользователь
        if mute_manager.is_muted(chat_id, user_id, current_time):
            try:
                await event.message.delete()
                logger.info(f"Удалено сообщение замученного пользователя {user_id} в чате {chat_id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение замученного пользователя: {e}")
            return
        
        # Проверяем на флуд
        if mute_manager.check_flood(chat_id, user_id, current_time):
            mute_info = mute_manager.mute_user(chat_id, user_id, user_name, chat_title, current_time)
            
            # Удаляем текущее сообщение
            try:
                await event.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
            
            mute_end_str = mute_info['mute_end'].strftime("%d.%m.%Y %H:%M:%S")
            mute_duration_str = "24 часа" if mute_info['duration'].days > 0 else "30 минут"
            
            private_message = (
                f"🚫 **ВЫ ПОЛУЧИЛИ МУТ**\n\n"
                f"Чат: {chat_title}\n"
                f"Причина: {mute_info['reason']}\n"
                f"Длительность: {mute_duration_str}\n"
                f"Окончание мута: {mute_end_str}\n"
                f"Нарушений за 24 часа: {mute_info['mute_count']}/3\n\n"
                f"Пожалуйста, не флудите в чате!"
            )
            
            # Отправляем личное сообщение
            try:
                await bot.send_message(
                    user_id=user_id,
                    text=private_message,
                    parse_mode=parse_mode.ParseMode.MARKDOWN
                )
                logger.info(f"Отправлено уведомление о муте пользователю {user_id}")
            except Exception as e:
                logger.warning(f"Не удалось отправить личное сообщение пользователю {user_id}: {e}")
            
            # Отправляем уведомление в чат
            try:
                chat_notification = f"⚠️ Пользователь {user_name} получил мут на {mute_duration_str} за флуд."
                notification_message = await bot.send_message(
                    chat_id=chat_id,
                    text=chat_notification
                )
                
                # Получаем ID сообщения
                notification_id = None
                if hasattr(notification_message, 'message_id'):
                    notification_id = notification_message.message_id
                elif hasattr(notification_message, 'id'):
                    notification_id = notification_message.id
                elif isinstance(notification_message, dict):
                    notification_id = notification_message.get('message_id') or notification_message.get('id')
                
                # Удаляем уведомление через 10 секунд
                if notification_id:
                    async def delete_notification():
                        await asyncio.sleep(10)
                        try:
                            await bot.delete_message(
                                chat_id=chat_id,
                                message_id=notification_id
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось удалить уведомление: {e}")
                    
                    asyncio.create_task(delete_notification())
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление в чат: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка в anti_spam_handler: {e}")

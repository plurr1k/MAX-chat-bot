# by plurr1k
from config import dp
from maxapi import F, types
from maxapi.enums import parse_mode
from maxapi.types import MessageCreated
from commands.user_subscribed import user_subscribed
from mute_middleware import AntiSpamMiddleware

@dp.message_created(types.Command('help'))
async def help_command(event: MessageCreated):
    if await user_subscribed(event) == False:
        return

    """Обработчик команды /help"""
    response = (
        "🤖 *ПОМОЩЬ ПО КОМАНДАМ*\n\n"
        
        "👤 *Информация о пользователях:*\n"
        "/myinfo - Ваша полная информация\n"
        "/userinfo [ID/@username] - Полная информация о пользователе в группах бота\n\n"
        "/abitur [ID] - Информация о статусе поступления"

        "💬 *Управление чатами:*\n"
        "/chatinfo [Ничего/ID] - Информация о текущем чате либо о чате по ID\n"
        "/getid - ID текущего чата\n\n"

        "👥 *Участники чата:*\n"
        "/random - Случайный участник\n"
        "/count - Количество участников\n\n"

        "🕹 *Развлечения:*\n"
        "/game - Игра с вопросами (100 баллов)\n"
        "/окак - Вывод картинки окак\n"
        "/wifi - Получить доступ к вайфай(20 минут)\n\n"

        "🕹 *Команды админов:*\n"
        "/randomverify [CHAT_ID1] [CHAT_ID2] - Случайный верифицированный участник\n"
        "/chats - Вывод всех чатов бота\n"
        "/setchat - Установить основной чат\n"
        "/setverify - Установить количество дней верификации для основнного чата\n"


        "\n❓ *Помощь:*\n"
        "/help - Эта справка\n"
        "/start - Начальная информация"
    )
    
    await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)




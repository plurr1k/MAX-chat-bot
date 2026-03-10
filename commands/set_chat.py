from config import bot, dp
import config

from maxapi import F
from maxapi.types import MessageCreated
from maxapi.enums import chat_type, parse_mode
from utils.helpers import get_chat_info_safe, get_chat_title_by_id
from commands.get_all_bot_chats import get_all_bot_chats

@dp.message_created(F.message.body.text.startswith("/setchat"))
async def set_chat(event: MessageCreated):


    chat_id = event.message.recipient.chat_id
    chat = await bot.get_chat_by_id(chat_id)
    chat_info = await get_chat_info_safe(chat)

    if chat_info['type'] == chat_type.ChatType.CHANNEL:
        return
    
    if event.message.sender.user_id not in config.ADMINS_ID:
        return
     
    await get_all_bot_chats(event, False)

    
    text = event.message.body.text.strip()
    parts = text.split()

    if len(parts) > 2:
        await bot.send_message(
        user_id=event.message.sender.user_id,
        text =
            "❌ Слишком много аргументов\n\n" +
            "*Пример:*\n" +
            "`/setchat -123456789` - установить чат с ID -123456789 как основной",
            parse_mode=parse_mode.ParseMode.MARKDOWN)
        return
    
    # Если указан ID чата
    elif len(parts) == 2:

        try:
            int(parts[1])
        except ValueError:
            await bot.send_message(
                user_id=event.message.sender.user_id,
                text=(
                    "❌ Аргумент должен быть числом (ID чата)\n\n"
                    "*Пример:*\n"
                    "`/setchat -123456789` - установить чат с ID -123456789 как основной"
                ),
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        
        for this_chat in config.ALL_CHATS:
                chat_info = await get_chat_info_safe(this_chat)
                if chat_info["chat_id"] == int(parts[1]):
                    in_all_chats = True
                    MAIN_CHAT_ID = int(parts[1])
                    await bot.send_message(user_id=event.message.sender.user_id,
                        text= f"✅ Чат {await get_chat_title_by_id(MAIN_CHAT_ID)} установлен как основной\nID: `{MAIN_CHAT_ID}`",
                        parse_mode=parse_mode.ParseMode.MARKDOWN)
                    break
                else:
                    in_all_chats = False
                
        if not in_all_chats:
            await bot.send_message(user_id=event.message.sender.user_id,
            text= f"❌ Этого чата нет в списке бота",
            parse_mode=parse_mode.ParseMode.MARKDOWN)
    else:

        if chat_info['type'] == chat_type.ChatType.DIALOG:
            await event.message.answer("❌ Нельзя установить личный чат как основной")
            return
    
        config.MAIN_CHAT_ID = event.message.recipient.chat_id

        await bot.send_message(user_id=event.message.sender.user_id,
            text= f"✅ Чат {await get_chat_title_by_id(config.MAIN_CHAT_ID)} установлен как основной\nID: `{config.MAIN_CHAT_ID}`",
            parse_mode=parse_mode.ParseMode.MARKDOWN)
        await event.message.delete()


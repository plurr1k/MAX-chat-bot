# Send picture with meme

from config import bot, dp
from maxapi import F, types
from maxapi.types import MessageCreated
from maxapi.types.attachments.upload import AttachmentUpload, AttachmentPayload
from maxapi.enums.upload_type import UploadType
import json
from logger_config import logger
import config
from commands.user_subscribed import user_subscribed

@dp.message_created(types.Command('окак'))
async def okak_command(event: MessageCreated):
    """Вывод картинки мема окак и удаление команды"""
    if await user_subscribed(event) == False:
        return
    try:
        # Сначала удаляем сообщение с командой
        await event.message.delete()
        
        # Загружаем и отправляем фото
        upload_url = await bot.get_upload_url(type=UploadType.IMAGE)

        uploaded = await bot.upload_file(
            url=upload_url.url,
            path="images/okak.webp",
            type=UploadType.IMAGE
        )
        
        parse_uploaded = json.loads(uploaded)
        
        photo_id = list(parse_uploaded["photos"].keys())[0]
        token = parse_uploaded["photos"][photo_id]["token"]

        photo_attachment = AttachmentUpload(
            type=UploadType.IMAGE,
            payload=AttachmentPayload(token=token)
        )

        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text="",
            attachments=[photo_attachment]
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде /окак: {e}")
        if event.message.sender.user_id in config.ADMINS_ID:
            await bot.send_message(
                user_id=event.message.sender.user_id,
                text=f"❌ Ошибка в команде /окак: {str(e)[:100]}"
            )

# by plurr1k
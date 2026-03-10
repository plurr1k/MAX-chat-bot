import asyncio
from config import bot, dp

# import commands
from commands import start_command
from commands import view_dz_command
from commands import help_command
from commands import get_all_bot_chats
from commands import set_chat
from commands import user_full_info_command
from commands import myinfo_command
from commands import chatinfo_command
from commands import okak_command
from commands import getid_command
from commands import count_command
from commands import random_member_command
from commands import handle_btn_rnd
from commands import set_verify_days
from commands import randomverify_command
from commands import randomverify_callback_handler

async def main():
    await dp.start_polling(bot, skip_updates=True)
if __name__=="__main__":
    asyncio.run(main())

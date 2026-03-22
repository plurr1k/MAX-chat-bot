# by plurr1k
import asyncio
from config import bot, dp
from mute_middleware import AntiSpamMiddleware
from utils.game_stats import GameStats
from maxapi.types import MessageCreated
#commands
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
from commands import botwifi
from commands import randomverify_command
from commands import randomverify_callback_handler
from commands import game
from commands import user_subscribed
from commands import abitur_command

async def main():
    dp.middleware(AntiSpamMiddleware())
    await dp.start_polling(bot, skip_updates=True)
    
if __name__=="__main__":
    asyncio.run(main())

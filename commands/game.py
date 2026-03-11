import random
from config import dp, bot
from logger_config import logger
from maxapi import F
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
import asyncio
import json
from utils import game_stats as gs
from typing import Dict

# ========== ЗАГРУЗКА ВОПРОСОВ ДЛЯ ИГРЫ ==========

def load_questions():
    """Загрузка вопросов из файла"""
    try:
        with open('jsons/questions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл questions.json не найден")
        return {"questions": [], "super_question": {}}
    except Exception as e:
        logger.error(f"Ошибка загрузки вопросов: {e}")
        return {"questions": [], "super_question": {}}

questions_data = load_questions()

# Словарь для хранения активных игр
active_games = {}

# Система подсчета очков
SCORES = [10, 30, 60, 120, 180, 240]
SUPER_SCORES = [400, 300, 200, 100, 50, 10]

class GameSession:
    def __init__(self, user_id: int, user_name: str):
        self.user_id = user_id
        self.user_name = user_name
        self.stage = "confirm"
        self.questions = random.sample(questions_data["questions"], 3)
        self.current_question_index = 0
        self.score = 0
        self.super_game_score = 0
        self.total_score = 0
        self.super_game_active = False
        self.bot_message_id = None
        
    def get_current_question(self):
        if self.super_game_active:
            return questions_data["super_question"]
        else:
            return self.questions[self.current_question_index]
    
    def check_answer(self, answer: str) -> Dict:
        question = self.get_current_question()
        answer_lower = answer.lower().strip()
        found_index = -1
        found_answer = None
        for i, ans in enumerate(question["answers"]):
            if ans.lower() == answer_lower or answer_lower in ans.lower():
                found_index = i
                found_answer = ans
                break
        if found_index == -1:
            return {"success": False, "message": "Ответ не найден в списке вариантов"}
        if self.super_game_active:
            points = SUPER_SCORES[found_index]
            self.super_game_score += points
            self.total_score += points
        else:
            points = SCORES[found_index]
            self.score += points
            self.total_score += points
        is_max = False
        if self.super_game_active:
            is_max = (points == SUPER_SCORES[0])
        else:
            is_max = (points == SCORES[5])
        if is_max:
            message = (
                f"🎉 **НЕВЕРОЯТНО!** Вы выбрали самый редкий ответ!\n"
                f"Ваш ответ: _{found_answer}_\n"
                f"➕ Вы получаете **{points}** очков!\n\n"
            )
        else:
            message = (
                f"✅ Принято! Ваш ответ: _{found_answer}_\n"
                f"➕ Очки: **{points}**\n\n"
            )
        if self.super_game_active:
            message += f"📊 Счет в супер-игре: {self.super_game_score}\n"
        message += f"📊 Общий счет: {self.total_score}"
        return {
            "success": True,
            "points": points,
            "answer": found_answer,
            "message": message,
            "is_max": is_max,
            "game_finished": self.check_game_finished()
        }
    
    def check_game_finished(self) -> bool:
        if self.super_game_active:
            return True
        if self.current_question_index >= 2:
            if self.score >= 600 and not self.super_game_active:
                return False
            return True
        return False
    
    def next_question(self):
        if not self.super_game_active:
            if self.current_question_index < 2:
                self.current_question_index += 1
            else:
                if self.score >= 600:
                    self.super_game_active = True
                    logger.info(f"Игрок {self.user_id} прошел в супер-игру с {self.score} очками")
                else:
                    self.stage = "finished"
        else:
            self.stage = "finished"

# ========== ИГРОВЫЕ КОМАНДЫ ==========

@dp.message_created(F.message.body.text == "/game")
async def game_command(event: MessageCreated):
    """Начало игры"""
    try:
        user_id = event.message.sender.user_id
        user_name = event.message.sender.first_name
        
        if not questions_data or not questions_data.get("questions"):
            await event.message.answer("❌ Игра временно недоступна. Вопросы не загружены.")
            return
        
        if user_id in active_games:
            await event.message.answer(
                "⚠️ У вас уже есть активная игра!\n"
                "Завершите текущую игру или подождите."
            )
            return
        
        active_games[user_id] = GameSession(user_id, user_name)
        
        response = (
            f"🎮 **ИГРА НАЧИНАЕТСЯ!**\n\n"
            f"Привет, {user_name}! Ты хочешь сыграть в игру?\n"
            f"Правила простые:\n"
            f"• Я задам тебе 3 вопроса\n"
            f"• У каждого вопроса 6 вариантов ответов\n"
            f"• Чем реже ответ, тем больше очков!\n"
            f"• Если наберешь 600+ очков, попадешь в СУПЕР-ИГРУ!\n\n"
            f"**Напиши ДА, чтобы продолжить**\n"
            f"**Напиши НЕТ, чтобы отказаться**"
        )
        
        sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
        message_id = None
        if hasattr(sent_message, 'message_id'):
            message_id = sent_message.message_id
        elif hasattr(sent_message, 'id'):
            message_id = sent_message.id
        elif isinstance(sent_message, dict):
            message_id = sent_message.get('message_id') or sent_message.get('id')
        
        if message_id:
            active_games[user_id].bot_message_id = message_id
            logger.info(f"Сохранен ID сообщения: {message_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в /game: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text.regexp(r'^(?:да|нет|ДА|НЕТ|Yes|NO|Да|Нет)$'))
async def game_confirm(event: MessageCreated):
    """Подтверждение начала игры"""
    try:
        user_id = event.message.sender.user_id
        
        if user_id not in active_games:
            return
        
        game = active_games[user_id]
        
        if game.stage != "confirm":
            return
        
        answer = event.message.body.text.lower()
        chat_id = event.message.recipient.chat_id
        
        if answer in ["да", "yes"]:
            try:
                await event.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение пользователя: {e}")
            
            if game.bot_message_id:
                try:
                    await bot.delete_message(
                        chat_id=chat_id,
                        message_id=game.bot_message_id
                    )
                    logger.info(f"Удалено сообщение бота: {game.bot_message_id}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение бота: {e}")
            
            game.stage = "playing"
            question = game.get_current_question()
            
            response = (
                f"**ВОПРОС №{game.current_question_index + 1}**\n\n"
                f"{question['question']}\n\n"
                f"**Варианты ответов:**\n"
            )
            
            for i, ans in enumerate(question['answers'], 1):
                response += f"{i}. {ans}\n"
            
            response += (
                f"\n📝 **Напиши ответ в виде:** `/otvet <твой ответ>`\n"
                f"Пример: `/otvet {question['answers'][0]}`"
            )
            
            sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
            
            message_id = None
            if hasattr(sent_message, 'message_id'):
                message_id = sent_message.message_id
            elif hasattr(sent_message, 'id'):
                message_id = sent_message.id
            elif isinstance(sent_message, dict):
                message_id = sent_message.get('message_id') or sent_message.get('id')
            
            if message_id:
                game.bot_message_id = message_id
                logger.info(f"Сохранен ID нового сообщения: {message_id}")
            
        elif answer in ["нет", "no"]:
            try:
                await event.message.delete()
            except:
                pass
            
            if game.bot_message_id:
                try:
                    await bot.delete_message(
                        chat_id=chat_id,
                        message_id=game.bot_message_id
                    )
                except:
                    pass
            
            del active_games[user_id]
            await event.message.answer("❌ Игра отменена. Если захочешь сыграть, просто напиши /game")
            
    except Exception as e:
        logger.error(f"Ошибка в подтверждении игры: {e}")

@dp.message_created(F.message.body.text.startswith("/otvet"))
async def game_answer(event: MessageCreated):
    """Обработка ответа на вопрос"""
    try:
        user_id = event.message.sender.user_id
        
        if user_id not in active_games:
            await event.message.answer("❌ У вас нет активной игры. Начните новую с помощью /game")
            return
        
        game = active_games[user_id]
        
        if game.stage not in ["playing", "super_game"]:
            await event.message.answer("❌ Сейчас не время для ответов. Дождитесь вопроса.")
            return
        
        text = event.message.body.text.strip()
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await event.message.answer(
                "❌ Напишите ответ в формате: `/otvet <ваш ответ>`",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        
        answer = parts[1]
        chat_id = event.message.recipient.chat_id
        
        result = game.check_answer(answer)
        
        if not result["success"]:
            await event.message.answer(result["message"])
            return
        
        try:
            await event.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить ответ пользователя: {e}")
        
        if game.bot_message_id:
            try:
                await bot.delete_message(
                    chat_id=chat_id,
                    message_id=game.bot_message_id
                )
                logger.info(f"Удалено сообщение бота с вопросом: {game.bot_message_id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение бота: {e}")
        
        sent_message = await event.message.answer(result["message"], parse_mode=parse_mode.ParseMode.MARKDOWN)
        
        message_id = None
        if hasattr(sent_message, 'message_id'):
            message_id = sent_message.message_id
        elif hasattr(sent_message, 'id'):
            message_id = sent_message.id
        elif isinstance(sent_message, dict):
            message_id = sent_message.get('message_id') or sent_message.get('id')
        
        if message_id:
            game.bot_message_id = message_id
            logger.info(f"Сохранен ID сообщения с результатом: {message_id}")
        
        if result["game_finished"]:
            gs.game_stats.add_score(user_id, game.user_name, game.total_score, game.super_game_active)
            
            if game.total_score >= 600 and game.super_game_active:
                response = (
                    f"🏆 **ПОБЕДА!** 🏆\n\n"
                    f"Ты прошел супер-игру!\n"
                    f"Итоговый счет: **{game.total_score}**\n\n"
                    f"Ты настоящий чемпион! 🎉"
                )
            else:
                response = (
                    f"🎯 **ИГРА ОКОНЧЕНА**\n\n"
                    f"Твой итоговый счет: **{game.total_score}**\n\n"
                )
                if game.total_score >= 600:
                    response += (
                        f"⭐ Ты набрал 600+ очков и прошел в супер-игру!\n"
                        f"Сыграй еще раз, чтобы покорить ее!"
                    )
                else:
                    response += (
                        f"В следующий раз повезет больше!\n"
                        f"Для новой игры используй /game"
                    )
            
            final_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
            
            final_message_id = None
            if hasattr(final_message, 'message_id'):
                final_message_id = final_message.message_id
            elif hasattr(final_message, 'id'):
                final_message_id = final_message.id
            elif isinstance(final_message, dict):
                final_message_id = final_message.get('message_id') or final_message.get('id')
            
            if final_message_id:
                async def delete_later():
                    await asyncio.sleep(30)
                    try:
                        await bot.delete_message(
                            chat_id=chat_id,
                            message_id=final_message_id
                        )
                        logger.info(f"Удалено финальное сообщение: {final_message_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить финальное сообщение: {e}")
                asyncio.create_task(delete_later())
            
            del active_games[user_id]
            logger.info(f"Игровая сессия для пользователя {user_id} удалена")
            
        else:
            game.next_question()
            
            if game.stage == "super_game":
                question = game.get_current_question()
                
                response = (
                    f"🌟 **СУПЕР-ИГРА!** 🌟\n\n"
                    f"{question['question']}\n\n"
                    f"**Варианты ответов:**\n"
                )
                
                for i, ans in enumerate(question['answers'], 1):
                    response += f"{i}. {ans}\n"
                
                response += (
                    f"\n📝 В супер-игре **самый популярный** ответ дает 400 очков!\n"
                    f"Напиши: `/otvet <твой ответ>`"
                )
                
                sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
                
                message_id = None
                if hasattr(sent_message, 'message_id'):
                    message_id = sent_message.message_id
                elif hasattr(sent_message, 'id'):
                    message_id = sent_message.id
                elif isinstance(sent_message, dict):
                    message_id = sent_message.get('message_id') or sent_message.get('id')
                
                if message_id:
                    game.bot_message_id = message_id
                
            elif game.stage == "playing":
                question = game.get_current_question()
                
                response = (
                    f"**ВОПРОС №{game.current_question_index + 1}**\n\n"
                    f"{question['question']}\n\n"
                    f"**Варианты ответов:**\n"
                )
                
                for i, ans in enumerate(question['answers'], 1):
                    response += f"{i}. {ans}\n"
                
                response += f"\n📝 `/otvet <твой ответ>`"
                
                sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
                
                message_id = None
                if hasattr(sent_message, 'message_id'):
                    message_id = sent_message.message_id
                elif hasattr(sent_message, 'id'):
                    message_id = sent_message.id
                elif isinstance(sent_message, dict):
                    message_id = sent_message.get('message_id') or sent_message.get('id')
                
                if message_id:
                    game.bot_message_id = message_id
        
    except Exception as e:
        logger.error(f"Ошибка в обработке ответа: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text == "/stats")
async def game_stats_command(event: MessageCreated):
    """Просмотр статистики игрока"""
    try:
        user_id = event.message.sender.user_id
        user_name = event.message.sender.first_name
        
        stats = gs.game_stats.get_user_stats(user_id)
        
        if not stats or not stats.get("games"):
            await event.message.answer(
                f"📊 **Статистика игрока {user_name}**\n\n"
                f"Вы еще не сыграли ни одной игры.\n"
                f"Начните с /game!"
            )
            return
        
        games_played = len(stats["games"])
        best_score = stats["best_score"]
        last_game = stats["games"][-1]
        
        response = (
            f"📊 **Статистика игрока {user_name}**\n\n"
            f"🎮 Сыграно игр: {games_played}\n"
            f"🏆 Лучший результат: {best_score}\n"
            f"📅 Последняя игра: {last_game['date']}\n"
            f"   • Счет: {last_game['score']}\n"
            f"   • Супер-игра: {'✅ Да' if last_game['super_game'] else '❌ Нет'}\n"
        )
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text == "/top")
async def game_top_command(event: MessageCreated):
    """Топ игроков"""
    try:
        stats = gs.game_stats.scores
        
        if not stats:
            await event.message.answer("📊 Пока нет статистики игр.")
            return
        
        top_players = sorted(
            stats.items(),
            key=lambda x: x[1]["best_score"],
            reverse=True
        )[:10]
        
        response = "🏆 **ТОП-10 ИГРОКОВ** 🏆\n\n"
        
        for i, (user_id, data) in enumerate(top_players, 1):
            response += f"{i}. {data['name']} — **{data['best_score']}** очков\n"
            response += f"   🎮 Игр: {len(data['games'])}\n"
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /top: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")
import random
from config import dp, bot
from logger_config import logger
from maxapi import F
from maxapi.types import MessageCreated
from maxapi.enums import parse_mode
import asyncio
import json
import math
from utils import game_stats as gs
from typing import Dict, List, Tuple
from commands.user_subscribed import user_subscribed, get_user_info_safe
from datetime import datetime

# ========== ЗАГРУЗКА ВОПРОСОВ ДЛЯ ИГРЫ ==========

def load_questions():
    """Загрузка вопросов из файла"""
    try:
        with open('jsons/questions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл questions.json не найден")
        return {"questions": [], "super_questions": []}
    except Exception as e:
        logger.error(f"Ошибка загрузки вопросов: {e}")
        return {"questions": [], "super_questions": []}

questions_data = load_questions()

# Словарь для хранения активных игр
active_games = {}

# Система подсчета очков
SCORES = [10, 30, 60, 120, 180, 240]
SUPER_SCORES = [400, 300, 200, 100, 50, 10]
MAX_REGULAR_SCORE = 620  # Максимум в обычной игре (240+180+120+60+30? Нужно уточнить)
MAX_TOTAL_SCORE = 1120  # Максимум с супер-игрой (620 + 400)
THRESHOLD_SUPER_GAME = 600  # Порог для входа в супер-игру

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
        self.super_question = None
        
    def get_current_question(self):
        if self.super_game_active:
            return self.super_question
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
                f"*Игра для {self.user_name}*\n\n"
                f"🎉 **НЕВЕРОЯТНО!** Вы выбрали самый редкий ответ!\n"
                f"➕ Вы получаете **{points}** очков!\n\n"
            )
        else:
            message = (
                f"*Игра для {self.user_name}*\n"
                f"✅ Принято!"
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
            if self.score >= THRESHOLD_SUPER_GAME and not self.super_game_active:
                return False
            return True
        return False
    
    def next_question(self):
        if not self.super_game_active:
            if self.current_question_index < 2:
                self.current_question_index += 1
            else:
                if self.score >= THRESHOLD_SUPER_GAME:
                    self.super_game_active = True
                    if questions_data.get("super_questions"):
                        self.super_question = random.choice(questions_data["super_questions"])
                        logger.info(f"Игрок {self.user_id} прошел в супер-игру с {self.score} очками")
                    else:
                        logger.error("Нет доступных вопросов для супер-игры")
                        self.stage = "finished"
                else:
                    self.stage = "finished"
        else:
            self.stage = "finished"

# ========== ФУНКЦИИ ДЛЯ РАСЧЕТА РЕЙТИНГА ==========

def calculate_player_rating(user_id: int, user_data: dict) -> float:
    """
    Расчет комплексного рейтинга игрока
    Возвращает число от 0 до 1000
    """
    games = user_data.get("games", [])
    if not games:
        return 0
    
    total_games = len(games)
    
    # 1. Процент идеальных игр (1120)
    perfect_games = sum(1 for game in games if game.get("score", 0) >= MAX_TOTAL_SCORE)
    perfect_games_ratio = perfect_games / total_games if total_games > 0 else 0
    
    # 2. Средний результат
    avg_score = sum(game.get("score", 0) for game in games) / total_games
    
    # 3. Нормализованный средний результат (в процентах от максимума 1120)
    avg_score_percentage = (avg_score / MAX_TOTAL_SCORE) * 100
    
    # 4. Коэффициент стабильности (чем меньше разброс, тем лучше)
    if total_games > 1:
        scores = [game.get("score", 0) for game in games]
        variance = sum((s - avg_score) ** 2 for s in scores) / total_games
        std_deviation = math.sqrt(variance)
        # Нормализуем стандартное отклонение (меньше = лучше)
        stability_factor = max(0, 100 - min(100, (std_deviation / MAX_TOTAL_SCORE) * 100))
    else:
        stability_factor = 100  # Для одного игрока максимальная стабильность
    
    # 5. Коэффициент активности (поощрение за количество игр)
    activity_factor = min(100, math.log(total_games + 1, 2) * 20)
    
    # 6. Процент игр с супер-игрой (600+)
    super_game_games = sum(1 for game in games if game.get("score", 0) >= THRESHOLD_SUPER_GAME)
    super_game_ratio = super_game_games / total_games if total_games > 0 else 0
    
    # 7. Бонус за идеальные игры (дополнительный множитель)
    perfect_bonus = (perfect_games_ratio * 50)  # 5% бонус
    
    # Итоговый рейтинг (взвешенная сумма)
    rating = (
        (perfect_games_ratio * 250) +          # 25% - идеальные игры (1120)
        (avg_score_percentage * 2.5) +          # 25% - средний результат
        (stability_factor * 2) +                 # 20% - стабильность
        (activity_factor * 1.5) +                 # 15% - активность
        (super_game_ratio * 100) +                # 10% - достижение супер-игры
        perfect_bonus                             # 5% - бонус за идеальные игры
    )
    
    return round(rating, 2)

def get_detailed_player_stats(user_id: int, user_data: dict) -> dict:
    """Получение детальной статистики для отображения"""
    games = user_data.get("games", [])
    total_games = len(games)
    
    if total_games == 0:
        return {
            "total_games": 0,
            "max_score": 0,
            "avg_score": 0,
            "perfect_games": 0,
            "super_game_games": 0,
            "avg_score_percentage": 0,
            "stability": 0,
            "rating": 0
        }
    
    max_score = user_data.get("best_score", 0)
    
    # Игры с максимальным результатом (1120)
    perfect_games = sum(1 for game in games if game.get("score", 0) == MAX_TOTAL_SCORE)
    
    # Игры с прохождением порога в супер-игру (600+)
    super_game_games = sum(1 for game in games if game.get("score", 0) >= THRESHOLD_SUPER_GAME)
    
    avg_score = sum(game.get("score", 0) for game in games) / total_games
    
    # Расчет стабильности
    if total_games > 1:
        scores = [game.get("score", 0) for game in games]
        variance = sum((s - avg_score) ** 2 for s in scores) / total_games
        std_deviation = math.sqrt(variance)
        stability = max(0, 100 - min(100, (std_deviation / MAX_TOTAL_SCORE) * 100))
    else:
        stability = 100
    
    rating = calculate_player_rating(user_id, user_data)
    
    return {
        "total_games": total_games,
        "max_score": max_score,
        "avg_score": round(avg_score, 1),
        "perfect_games": perfect_games,
        "super_game_games": super_game_games,
        "avg_score_percentage": round((avg_score / MAX_TOTAL_SCORE) * 100, 1),
        "stability": round(stability, 1),
        "rating": rating
    }

def get_rating_tier(rating: float) -> str:
    """Определение лиги игрока по рейтингу"""
    if rating >= 900:
        return "👑 Легенда"
    elif rating >= 750:
        return "💎 Мастер"
    elif rating >= 600:
        return "🥈 Профи"
    elif rating >= 400:
        return "🥉 Любитель"
    elif rating >= 200:
        return "📚 Новичок"
    else:
        return "🌱 Ученик"

def get_rating_stars(rating: float) -> str:
    """Получение визуального отображения рейтинга звездами"""
    filled_stars = int(rating / 100)  # Количество заполненных звезд (от 0 до 10)
    empty_stars = 10 - filled_stars
    return "⭐" * filled_stars + "☆" * empty_stars

# ========== ИГРОВЫЕ КОМАНДЫ ==========

@dp.message_created(F.message.body.text == "/game")
async def game_command(event: MessageCreated):
    if await user_subscribed(event) == False:
        return
    """Начало игры"""
    try:
        user_id = event.message.sender.user_id
        user_name = event.message.sender.first_name
        await event.message.delete()
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
            f"Привет, {event.message.sender.full_name}! Ты хочешь сыграть в игру?\n"
            f"Правила простые:\n"
            f"• Я задам тебе 3 вопроса\n"
            f"• У каждого вопроса 6 вариантов ответов\n"
            f"• Чем реже ответ, тем больше очков!\n"
            f"• Максимум в обычной игре: **{MAX_REGULAR_SCORE} очков**\n"
            f"• Если наберешь **{THRESHOLD_SUPER_GAME}+ очков**, попадешь в СУПЕР-ИГРУ!\n"
            f"• В супер-игре можно набрать еще **400 очков**\n"
            f"• Абсолютный максимум: **{MAX_TOTAL_SCORE} очков**!\n"
            f"• Для ответа используй команду: **/о <твой ответ>** (можно писать /o латиницей)\n"
            f"• Для досрочного завершения игры используй /stopgame\n\n"
            f"**Напиши ДА, чтобы продолжить**\n"
            f"**Напиши НЕТ, чтобы отказаться**"
        )
        
        sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
        message_id = sent_message.message.body.mid
        
        if message_id:
            active_games[user_id].bot_message_id = message_id
            logger.info(f"Сохранен ID сообщения: {message_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в /game: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text == "/stopgame")
async def stop_game_command(event: MessageCreated):
    """Принудительное завершение игры"""
    try:
        user_id = event.message.sender.user_id
        user_name = event.message.sender.first_name
        
        if user_id not in active_games:
            await event.message.answer(
                "❌ У вас нет активной игры.\n"
                "Начните новую игру с помощью /game"
            )
            return
        if msg_bad_answer is not None:
            await bot.delete_message(message_id = msg_bad_answer)
        game = active_games[user_id]
        
        if game.total_score > 0:
            gs.game_stats.add_score(user_id, user_name, game.total_score, game.super_game_active)
            
            response = (
                f"🛑 **ИГРА ПРЕРВАНА**\n\n"
                f"Игрок: {event.message.sender.full_name}\n"
                f"Ваш итоговый счет: **{game.total_score}** (максимум: {MAX_TOTAL_SCORE})\n"
                f"Пройдено вопросов: {game.current_question_index + 1}\n"
                f"{'✅ Были в супер-игре' if game.super_game_active else '❌ Супер-игра не достигнута'}\n\n"
                f"/stats - для вывода статистики\n"
                f"/top - топ 15 игроков\n"
                f"Для новой игры используйте /game\n"
            )
        else:
            response = (
                f"🛑 **ИГРА ПРЕРВАНА**\n"
                f"*Игра для {event.message.sender.full_name}*\n\n"
                f"Вы завершили игру, не набрав очков.\n"
                f"Статистика не сохранена.\n"
                f"Для новой игры используйте /game"
            )
        
        if game.bot_message_id:
            try:
                await bot.delete_message(message_id=game.bot_message_id)
            except:
                pass
        
        try:
            await event.message.delete()
        except:
            pass
        
        final_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
        del active_games[user_id]
        logger.info(f"Игровая сессия для пользователя {user_id} принудительно завершена")
        
        final_message_id = final_message.message.body.mid
        if final_message_id:
            async def delete_later():
                await asyncio.sleep(30)
                try:
                    await bot.delete_message(message_id=final_message_id)
                except:
                    pass
            asyncio.create_task(delete_later())
        
    except Exception as e:
        logger.error(f"Ошибка в /stopgame: {e}")
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
        
        if answer in ["да", "yes"]:
            try:
                await event.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение пользователя: {e}")
            
            if game.bot_message_id:
                try:
                    await bot.delete_message(
                        message_id=game.bot_message_id
                    )
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение бота: {e}")
            
            game.stage = "playing"
            question = game.get_current_question()
            
            response = (
                f"**ВОПРОС №{game.current_question_index + 1}**\n"
                f"*Игра для {event.message.sender.full_name}*\n\n"
                f"{question['question']}\n\n"
                f"**Варианты ответов:**\n"
            )
            
            for i, ans in enumerate(question['answers'], 1):
                response += f"{i}. {ans}\n"
            
            response += (
                f"\n📝 **Напиши ответ в виде:** `/о <твой ответ>`\n"
                f"Пример: `/о {question['answers'][0]}`\n"
                f"Можно также использовать `/o` латиницей\n"
                f"🛑 Для выхода из игры используй /stopgame"
            )
            
            sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
            message_id = sent_message.message.body.mid
            
            game.bot_message_id = message_id
            
        elif answer in ["нет", "no"]:
            try:
                await event.message.delete()
            except:
                pass
            
            if game.bot_message_id:
                try:
                    await bot.delete_message(
                        message_id=game.bot_message_id
                    )
                except:
                    pass
            
            del active_games[user_id]
            await event.message.answer("❌ *{event.message.sender.full_name}*, игра отменена. Если захочешь сыграть, просто напиши /game", parse_mode=parse_mode.ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Ошибка в подтверждении игры: {e}")
    
result_message_id = None
msg_bad_answer = None
@dp.message_created(F.message.body.text.startswith(("/о ", "/o ", "/о", "/o")))
async def game_answer(event: MessageCreated):
    """Обработка ответа на вопрос (команды /о и /o)"""
    try:
        global result_message_id, msg_bad_answer

        user_id = event.message.sender.user_id

        if user_id not in active_games:
            await bot.delete_message(message_id = event.message.body.mid)
            await event.message.answer(f"❌ *{event.message.sender.full_name}*, у вас нет активной игры. Начните новую с помощью /game", parse_mode=parse_mode.ParseMode.MARKDOWN)
            return
        
        game = active_games[user_id]
        
        if game.stage not in ["playing", "super_game"]:
            await bot.delete_message(message_id = event.message.body.mid)
            await event.message.answer(f"*❌{event.message.sender.full_name}*, Сейчас не время для ответов. Дождитесь вопроса.", parse_mode=parse_mode.ParseMode.MARKDOWN)
            return
        await bot.delete_message(message_id = event.message.body.mid)
        if msg_bad_answer is not None:
            await bot.delete_message(message_id = msg_bad_answer)
        text = event.message.body.text.strip()
        
        # Определяем, какая команда использована и извлекаем ответ
        if text.startswith("/о "):
            parts = text[3:].strip()  # Убираем "/о " и пробелы
        elif text.startswith("/o "):
            parts = text[3:].strip()  # Убираем "/o " и пробелы
        elif text == "/о" or text == "/o":
            parts = ""  # Команда без аргументов
        else:
            # На случай если команда написана слитно или с другими вариациями
            parts = text[2:].strip() if len(text) > 2 else ""
        
        if not parts:
            await event.message.answer(
                "❌ Напишите ответ в формате: `/о <ваш ответ>` или `/o <ваш ответ>`\n"
                f"Пример: `/о {game.get_current_question()['answers'][0]}`",
                parse_mode=parse_mode.ParseMode.MARKDOWN
            )
            return
        
        answer = parts

        result = game.check_answer(answer)
        if not result["success"]:
            await event.message.delete()
            msg_bad_answer = await event.message.answer(f"*Игра для {event.message.sender.full_name}*\n❌ " + result["message"], parse_mode=parse_mode.ParseMode.MARKDOWN)
            msg_bad_answer = msg_bad_answer.message.body.mid
            return
        
        if result_message_id is not None:
            try:
                await bot.delete_message(
                    message_id=result_message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение бота: {e}")

        if game.bot_message_id:
            try:
                await bot.delete_message(
                    message_id=game.bot_message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение бота: {e}")
        
        result_message = await event.message.answer(result["message"], parse_mode=parse_mode.ParseMode.MARKDOWN)
        
        result_message_id = result_message.message.body.mid
        
        if result["game_finished"]:
            gs.game_stats.add_score(user_id, game.user_name, game.total_score, game.super_game_active)
            
            await bot.delete_message(
                message_id=result_message_id
            )

            if game.total_score == MAX_TOTAL_SCORE:
                response = (
                    f"🏆 **АБСОЛЮТНАЯ ПОБЕДА!** 🏆\n\n"
                    f"*{event.message.sender.full_name}*, ты набрал максимально возможное количество очков!\n"
                    f"Итоговый счет: **{game.total_score}** из {MAX_TOTAL_SCORE}\n"
                    f"/stats - для вывода статистики\n"
                    f"/top - топ 15 игроков\n"
                    f"ТЫ ЛЕГЕНДА! 👑\n"
                )
            elif game.total_score >= THRESHOLD_SUPER_GAME and game.super_game_active:
                response = (
                    f"🎉 **ПОБЕДА!** 🎉\n\n"
                    f"*{event.message.sender.full_name}*, ты прошел супер-игру!\n"
                    f"Итоговый счет: **{game.total_score}** из {MAX_TOTAL_SCORE}\n"
                    f"Ты настоящий чемпион! ⭐\n"
                    f"/stats - для вывода статистики\n"
                    f"/top - топ 15 игроков\n"
                )
            else:
                response = (
                    f"🎯 **ИГРА ОКОНЧЕНА**\n"
                    f"*Игра для {event.message.sender.full_name}*\n\n"
                    f"Твой итоговый счет: **{game.total_score}** из {MAX_TOTAL_SCORE}\n"
                )
                if game.total_score >= THRESHOLD_SUPER_GAME:
                    response += (
                        f"⭐ *{event.message.sender.full_name}*, ты набрал {THRESHOLD_SUPER_GAME}+ очков и прошел в супер-игру!\n"
                        f"Сыграй еще раз (/game), чтобы покорить абсолютный максимум!\n"
                        f"/stats - для вывода статистики\n"
                        f"/top - топ 15 игроков\n"
                    )
                else:
                    response += (
                        f"В следующий раз повезет больше! Нужно {THRESHOLD_SUPER_GAME} очков для супер-игры.\n"
                        f"/stats - для вывода статистики\n"
                        f"/top - топ 15 игроков\n"
                        f"Для новой игры используй /game\n"
                    )
            
            final_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
            
            final_message_id = final_message.message.body.mid
            
            if final_message_id:
                async def delete_later():
                    await asyncio.sleep(30)
                    try:
                        await bot.delete_message(
                            message_id=final_message_id
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось удалить финальное сообщение: {e}")
                asyncio.create_task(delete_later())
            
            del active_games[user_id]
            
        else:
            game.next_question()
            
            if game.stage == "super_game":
                question = game.get_current_question()
                
                response = (
                    f"🌟 **СУПЕР-ИГРА!** 🌟\n"
                    f"*Игра для {event.message.sender.full_name}*\n\n"
                    f"{question['question']}\n\n"
                    f"**Варианты ответов:**\n"
                )
                
                for i, ans in enumerate(question['answers'], 1):
                    response += f"{i}. {ans}\n"
                
                response += (
                    f"\n📝 В супер-игре **самый популярный** ответ дает 400 очков!\n"
                    f"**Самый редкий** ответ дает 10 очков.\n"
                    f"Максимум за супер-игру: 400 очков\n"
                    f"Общий максимум: {MAX_TOTAL_SCORE} очков\n"
                    f"Напиши: `/о <твой ответ>` или `/o <твой ответ>`\n"
                    f"🛑 Для выхода из игры используй /stopgame"
                )
                
                sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
                
                message_id = sent_message.message.body.mid
                
                if message_id:
                    game.bot_message_id = message_id
                
            elif game.stage == "playing":
                question = game.get_current_question()
                
                response = (
                    f"**ВОПРОС №{game.current_question_index + 1}**\n"
                    f"*Игра для {event.message.sender.full_name}*\n\n"
                    f"{question['question']}\n\n"
                    f"**Варианты ответов:**\n"
                )
                
                for i, ans in enumerate(question['answers'], 1):
                    response += f"{i}. {ans}\n"
                
                response += f"\n📝 `/о <твой ответ>` или `/o <твой ответ>`\n"
                response += f"🛑 Для выхода из игры используй /stopgame"
                
                sent_message = await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
                
                message_id = sent_message.message.body.mid
                
                if message_id:
                    game.bot_message_id = message_id
        
    except Exception as e:
        logger.error(f"Ошибка в обработке ответа: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text == "/stats")
async def game_stats_command(event: MessageCreated):
    if await user_subscribed(event) == False:
        return
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
        
        detailed = get_detailed_player_stats(user_id, stats)
        rating_tier = get_rating_tier(detailed["rating"])
        rating_stars = get_rating_stars(detailed["rating"])
        
        response = (
            f"🎮 **{user_name}**\n"
            f"{rating_tier}\n"
            f"🏆 Рейтинг: {detailed['rating']}\n"
            f"{rating_stars}\n"
            f"├─ 🎯 Игр: {detailed['total_games']} (идеальных: {detailed['perfect_games']})\n"
            f"├─ 🎯 Супер-игр: {detailed['super_game_games']}\n"
            f"├─ 📊 Средний счет: {detailed['avg_score']} ({detailed['avg_score_percentage']}%)\n"
            f"├─ 🏆 Лучший счет: {detailed['max_score']}\n"
            f"└─ 📈 Стабильность: {detailed['stability']}%"
        )
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message_created(F.message.body.text == "/top")
async def game_top_command(event: MessageCreated):
    """Топ игроков по комплексному рейтингу"""
    try:
        stats = gs.game_stats.scores
        
        if not stats:
            await event.message.answer("📊 Пока нет статистики игр.")
            return
        
        # Рассчитываем рейтинг для каждого игрока
        players_with_rating = []
        for user_id, user_data in stats.items():
            if user_data.get("games"):  # Только игроки с хотя бы одной игрой
                rating = calculate_player_rating(user_id, user_data)
                detailed = get_detailed_player_stats(user_id, user_data)
                players_with_rating.append({
                    "name": user_data.get("name", "Неизвестный"),
                    "rating": rating,
                    "tier": get_rating_tier(rating),
                    "stars": get_rating_stars(rating)
                })
        
        # Сортируем по рейтингу (от большего к меньшему)
        top_players = sorted(players_with_rating, key=lambda x: x["rating"], reverse=True)[:15]
        
        response = "🏆 **ТОП-15 ИГРОКОВ** 🏆\n\n"
        
        # Добавляем топ игроков
        for i, player in enumerate(top_players, 1):
            # Определяем медаль для первых трех мест
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            response += (
                f"{medal} **{player['name']}**\n"
                f"{player['tier']}\n"
                f"⚡ Рейтинг: {player['rating']}\n"
                f"{player['stars']}\n\n"
            )
        
        await event.message.answer(response, parse_mode=parse_mode.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка в /top: {e}")
        await event.message.answer(f"❌ Ошибка: {str(e)[:100]}")

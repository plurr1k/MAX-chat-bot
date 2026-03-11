# game_stats.py
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class GameStats:
    def __init__(self, filename="jsons/game_scores.json"):
        self.filename = filename
        self.scores = self.load_scores()
    
    def load_scores(self) -> Dict:
        """Загрузка результатов игр"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_scores(self):
        """Сохранение результатов"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=4)
    
    def add_score(self, user_id: int, user_name: str, score: int, super_game: bool = False):
        """Добавление результата игры"""
        user_id_str = str(user_id)
        if user_id_str not in self.scores:
            self.scores[user_id_str] = {
                "name": user_name,
                "games": [],
                "best_score": 0
            }
        
        game_result = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": score,
            "super_game": super_game
        }
        
        self.scores[user_id_str]["games"].append(game_result)
        
        # Обновляем лучший результат
        if score > self.scores[user_id_str]["best_score"]:
            self.scores[user_id_str]["best_score"] = score
        
        self.save_scores()
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        user_id_str = str(user_id)
        return self.scores.get(user_id_str, {})

# Глобальный объект для статистики
game_stats = GameStats()
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# На Render: установи DATA_DIR=/data (с Render Disk) или оставь по умолчанию
_data_dir = Path(os.getenv("DATA_DIR", "."))
_data_dir.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = _data_dir / "progress_smc.json"

DEFAULT_DEADLINE_DAYS = 7
MAX_EXTENSIONS = 3

user_progress: Dict[int, Dict[str, Any]] = {}


def load_progress():
    global user_progress
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            user_progress = {int(k): v for k, v in data.items()}
            logger.info(f"Прогресс загружен: {len(user_progress)} пользователей")
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
            user_progress = {}
    else:
        logger.info("Файл прогресса не найден, начинаем с нуля")


def save_progress():
    try:
        tmp = PROGRESS_FILE.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(user_progress, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(PROGRESS_FILE)
    except Exception as e:
        logger.error(f"Ошибка сохранения прогресса: {e}")


def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_progress:
        user_progress[user_id] = {
            "name": str(user_id),
            "xp": 0,
            "level": 1,
            "rank": "🪨 Новичок",
            "module_index": 0,
            "completed_quests": [],
            "active_quest": None,
            "homework_status": "idle",
            "module_deadline": None,
            "deadline_extensions": 0,
            "quiz_state": None,
        }
    return user_progress[user_id]


RANKS = [
    (0,    "🪨 Новичок"),
    (100,  "⚔️ Стажёр"),
    (250,  "🥉 Аналитик"),
    (500,  "🥈 Трейдер"),
    (900,  "🥇 Профи"),
    (1500, "💎 Мастер SMC"),
    (2500, "🔮 Архитектор рынка"),
]


def get_rank(xp: int) -> str:
    rank = RANKS[0][1]
    for threshold, title in RANKS:
        if xp >= threshold:
            rank = title
    return rank


def add_xp(user_id: int, amount: int):
    state = get_user_state(user_id)
    state["xp"] += amount
    old_level = state["level"]
    state["level"] = 1 + state["xp"] // 100
    state["rank"] = get_rank(state["xp"])
    save_progress()
    leveled_up = state["level"] > old_level
    return state["level"], leveled_up


def set_module_deadline(state: Dict[str, Any], days: int = DEFAULT_DEADLINE_DAYS):
    deadline = datetime.utcnow() + timedelta(days=days)
    state["module_deadline"] = deadline.isoformat()


def is_deadline_expired(state: Dict[str, Any]) -> bool:
    dl = state.get("module_deadline")
    if not dl:
        return False
    try:
        return datetime.utcnow() > datetime.fromisoformat(dl)
    except Exception:
        return False


def reset_user_progress(user_id: int):
    state = get_user_state(user_id)
    state.update({
        "xp": 0, "level": 1, "rank": "🪨 Новичок",
        "module_index": 0, "completed_quests": [],
        "active_quest": None, "homework_status": "idle",
        "module_deadline": None, "deadline_extensions": 0,
        "quiz_state": None,
    })
    save_progress()


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    entries = [
        {
            "user_id": uid,
            "name": st.get("name", str(uid)),
            "xp": st.get("xp", 0),
            "level": st.get("level", 1),
            "rank": st.get("rank", "🪨 Новичок"),
            "module": st.get("module_index", 0) + 1,
        }
        for uid, st in user_progress.items()
    ]
    return sorted(entries, key=lambda x: x["xp"], reverse=True)[:limit]


load_progress()

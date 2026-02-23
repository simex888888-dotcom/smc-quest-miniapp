import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
PROGRESS_FILE = Path("progress_smc.json")

DEFAULT_DEADLINE_DAYS = 7
MAX_EXTENSIONS = 3

user_progress: Dict[int, Dict[str, Any]] = {}


def load_progress():
    global user_progress
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            user_progress = {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
            user_progress = {}


def save_progress():
    try:
        PROGRESS_FILE.write_text(
            json.dumps(user_progress, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
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
    (0,   "🪨 Новичок"),
    (100, "⚔️ Стажёр"),
    (250, "🥉 Аналитик"),
    (500, "🥈 Трейдер"),
    (900, "🥇 Профи"),
    (1500,"💎 Мастер SMC"),
    (2500,"🔮 Архитектор рынка"),
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
    state["xp"] = 0
    state["level"] = 1
    state["rank"] = "🪨 Новичок"
    state["module_index"] = 0
    state["completed_quests"] = []
    state["active_quest"] = None
    state["homework_status"] = "idle"
    state["module_deadline"] = None
    state["deadline_extensions"] = 0
    state["quiz_state"] = None
    save_progress()


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    entries = []
    for uid, st in user_progress.items():
        entries.append({
            "user_id": uid,
            "name": st.get("name", str(uid)),
            "xp": st.get("xp", 0),
            "level": st.get("level", 1),
            "rank": st.get("rank", "🪨 Новичок"),
            "module": st.get("module_index", 0) + 1,
        })
    return sorted(entries, key=lambda x: x["xp"], reverse=True)[:limit]


load_progress()

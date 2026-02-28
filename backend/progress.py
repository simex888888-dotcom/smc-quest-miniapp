import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

_data_dir = Path(os.getenv("DATA_DIR", "."))
_data_dir.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = _data_dir / "progress_smc.json"

# ── CONSTANTS ────────────────────────────────────────────────────────────────
DEFAULT_DEADLINE_HOURS = 72   # 72 hours per module (the market doesn't wait)
MAX_EXTENSIONS = 1            # Only ONE extension per module — then full repurchase
DAILY_BONUS_XP = 20           # XP for daily login streak
REFERRAL_BONUS_XP = 300       # XP for inviting a friend

# Per-module penalty amounts (USD) — "биржевая комиссия за промедление"
MODULE_PENALTIES = {
    0: 0,   # Free module
    1: 3,
    2: 3,
    3: 5,
    4: 5,
    5: 5,
    6: 7,
    7: 7,
    8: 10,
    9: 10,
}
MODULE_FULL_REPURCHASE = {
    0: 0,
    1: 9,
    2: 9,
    3: 12,
    4: 12,
    5: 12,
    6: 15,
    7: 15,
    8: 19,
    9: 29,   # Final exam module
}

# ── SMC TRADER LEVELS — 7 levels from Observer to Market Architect ────────
SMC_LEVELS: List[Tuple[int, int, str]] = [
    (0,    1, "Наблюдатель рынка"),
    (300,  2, "Охотник за ликвидностью"),
    (700,  3, "Снайпер ордер-блоков"),
    (1300, 4, "SMC Практик"),
    (2100, 5, "Smart Money Инсайдер"),
    (3200, 6, "Институциональный призрак"),
    (5000, 7, "Архитектор рынка"),
]

# ── BADGES ───────────────────────────────────────────────────────────────────
BADGE_DEFS = {
    "first_blood":      {"title": "Первая кровь",        "desc": "Первый квиз пройден"},
    "no_sleep":         {"title": "Без сна",             "desc": "Модуль завершён за одну сессию"},
    "iron_will":        {"title": "Железная воля",       "desc": "30 дней без пропусков"},
    "ghost":            {"title": "Призрак",             "desc": "Топ-1% недели"},
    "liquidity_hunter": {"title": "Охотник ликвидности", "desc": "10 sweep-уровней подряд"},
    "time_is_money":    {"title": "Время — деньги",      "desc": "Домашку сдал за первые 12 часов"},
    "chm_legend":       {"title": "Легенда CHM",         "desc": "Весь курс пройден"},
    "disciplined":      {"title": "Дисциплинированный трейдер", "desc": "Дедлайн выполнен вовремя"},
    "streak_7":         {"title": "Неделя без пропусков","desc": "7 дней активности подряд"},
    "streak_30":        {"title": "Железная воля",       "desc": "30 дней активности подряд"},
}

user_progress: Dict[int, Dict[str, Any]] = {}


# ── LOAD / SAVE ───────────────────────────────────────────────────────────────

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


# ── USER STATE ────────────────────────────────────────────────────────────────

def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_progress:
        user_progress[user_id] = {
            "name": str(user_id),
            "xp": 0,
            "level": 1,
            "rank": "Наблюдатель рынка",
            "module_index": 0,
            "completed_quests": [],
            "active_quest": None,
            "homework_status": "idle",
            "module_deadline": None,
            "deadline_extensions": 0,
            "quiz_state": None,
            # ── New fields ──
            "streak": 0,
            "last_active_date": None,
            "badges": [],
            "daily_bonus_claimed": None,
            "module_unlocked": [0],  # free module always unlocked
        }
    state = user_progress[user_id]
    # Back-compat: ensure new fields on old user records
    state.setdefault("streak", 0)
    state.setdefault("last_active_date", None)
    state.setdefault("badges", [])
    state.setdefault("daily_bonus_claimed", None)
    state.setdefault("module_unlocked", [0])
    return state


# ── LEVELS & RANKS ────────────────────────────────────────────────────────────

def get_level_and_rank(xp: int) -> Tuple[int, str]:
    level, rank = 1, "Наблюдатель рынка"
    for threshold, lvl, name in SMC_LEVELS:
        if xp >= threshold:
            level, rank = lvl, name
    return level, rank


def get_next_level_xp(current_xp: int) -> int:
    """Returns XP needed for next level. Returns -1 if max level."""
    for threshold, _lvl, _name in SMC_LEVELS:
        if threshold > current_xp:
            return threshold
    return -1


def add_xp(user_id: int, amount: int) -> Tuple[int, bool]:
    state = get_user_state(user_id)
    old_level = state["level"]
    state["xp"] += amount
    new_level, new_rank = get_level_and_rank(state["xp"])
    state["level"] = new_level
    state["rank"] = new_rank
    save_progress()
    leveled_up = new_level > old_level
    return new_level, leveled_up


# ── STREAK SYSTEM ─────────────────────────────────────────────────────────────

def update_streak(user_id: int) -> Tuple[int, bool]:
    """Update daily login streak. Returns (streak_count, is_new_day)."""
    state = get_user_state(user_id)
    today = date.today().isoformat()
    last = state.get("last_active_date")

    if last == today:
        return state["streak"], False   # already visited today

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if last == yesterday:
        state["streak"] = state.get("streak", 0) + 1
    else:
        state["streak"] = 1  # streak broken or first visit

    state["last_active_date"] = today

    streak = state["streak"]

    # Milestone badges & bonus XP
    if streak == 7 and "streak_7" not in state["badges"]:
        state["badges"].append("streak_7")
        state["xp"] += 100          # bonus XP for 7-day streak
        new_level, new_rank = get_level_and_rank(state["xp"])
        state["level"] = new_level
        state["rank"] = new_rank

    if streak == 30 and "iron_will" not in state["badges"]:
        state["badges"].append("iron_will")
        state["xp"] += 500          # bonus XP for 30-day streak
        new_level, new_rank = get_level_and_rank(state["xp"])
        state["level"] = new_level
        state["rank"] = new_rank

    save_progress()
    return streak, True


def claim_daily_bonus(user_id: int) -> Tuple[int, bool]:
    """Claim daily bonus XP (+20 XP). Returns (xp_earned, was_new)."""
    state = get_user_state(user_id)
    today = date.today().isoformat()

    if state.get("daily_bonus_claimed") == today:
        return 0, False

    state["daily_bonus_claimed"] = today
    add_xp(user_id, DAILY_BONUS_XP)
    return DAILY_BONUS_XP, True


# ── DEADLINE SYSTEM ───────────────────────────────────────────────────────────

def set_module_deadline(state: Dict[str, Any], hours: int = DEFAULT_DEADLINE_HOURS):
    """Set 72-hour deadline for a module. Module 0 (free) gets no deadline."""
    if state.get("module_index", 0) == 0:
        state["module_deadline"] = None   # free module — no timer
        return
    deadline = datetime.utcnow() + timedelta(hours=hours)
    state["module_deadline"] = deadline.isoformat()
    state["deadline_extensions"] = 0     # reset extensions for new module


def is_deadline_expired(state: Dict[str, Any]) -> bool:
    dl = state.get("module_deadline")
    if not dl:
        return False
    try:
        return datetime.utcnow() > datetime.fromisoformat(dl)
    except Exception:
        return False


def get_deadline_hours_remaining(state: Dict[str, Any]) -> float:
    """Returns hours remaining until deadline. +inf if no deadline. Negative if expired."""
    dl = state.get("module_deadline")
    if not dl:
        return float("inf")
    try:
        remaining = datetime.fromisoformat(dl) - datetime.utcnow()
        return remaining.total_seconds() / 3600
    except Exception:
        return float("inf")


def apply_penalty_extension(state: Dict[str, Any]) -> bool:
    """Apply 48-hour penalty extension (first miss). Returns False if already extended."""
    if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
        return False
    new_dl = datetime.utcnow() + timedelta(hours=48)
    state["module_deadline"] = new_dl.isoformat()
    state["deadline_extensions"] = state.get("deadline_extensions", 0) + 1
    return True


# ── BADGE SYSTEM ─────────────────────────────────────────────────────────────

def award_badge(user_id: int, badge_id: str) -> bool:
    """Award a badge. Returns True if newly awarded."""
    if badge_id not in BADGE_DEFS:
        return False
    state = get_user_state(user_id)
    if badge_id in state["badges"]:
        return False
    state["badges"].append(badge_id)
    save_progress()
    return True


# ── RESET ─────────────────────────────────────────────────────────────────────

def reset_user_progress(user_id: int):
    state = get_user_state(user_id)
    streak = state.get("streak", 0)
    last_active = state.get("last_active_date")
    badges = state.get("badges", [])
    state.update({
        "xp": 0, "level": 1, "rank": "Наблюдатель рынка",
        "module_index": 0, "completed_quests": [],
        "active_quest": None, "homework_status": "idle",
        "module_deadline": None, "deadline_extensions": 0,
        "quiz_state": None,
        # Preserve streak and badges on reset
        "streak": streak,
        "last_active_date": last_active,
        "badges": badges,
        "daily_bonus_claimed": None,
        "module_unlocked": [0],
    })
    save_progress()


# ── LEADERBOARD ───────────────────────────────────────────────────────────────

def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    entries = [
        {
            "user_id": uid,
            "name": st.get("name", str(uid)),
            "xp": st.get("xp", 0),
            "level": st.get("level", 1),
            "rank": st.get("rank", "Наблюдатель рынка"),
            "module": st.get("module_index", 0) + 1,
            "streak": st.get("streak", 0),
        }
        for uid, st in user_progress.items()
    ]
    return sorted(entries, key=lambda x: x["xp"], reverse=True)[:limit]


load_progress()

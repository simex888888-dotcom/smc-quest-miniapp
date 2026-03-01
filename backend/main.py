import os
import base64
import logging
import random
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from progress import (
    get_user_state, save_progress, add_xp,
    set_module_deadline, is_deadline_expired,
    reset_user_progress, get_leaderboard,
    user_progress, load_progress,
    MAX_EXTENSIONS, DEFAULT_DEADLINE_HOURS,
    update_streak, claim_daily_bonus, award_badge,
    get_deadline_hours_remaining, apply_penalty_extension,
    MODULE_PENALTIES, MODULE_FULL_REPURCHASE,
    BADGE_DEFS, SMC_LEVELS, get_level_and_rank,
)
from lessons import LESSONS, MODULES
from quests import QUESTS, QUIZZES
from charts import generate_chart
from bot import bot as telegram_bot, setup_webhook, process_update

app = FastAPI(title="CHM Smart Money Academy API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static frontend ───────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info(f"Frontend: {FRONTEND_DIR}")
else:
    logger.warning(f"Frontend folder not found: {FRONTEND_DIR}")


# ── REQUEST MODELS ────────────────────────────────────────────────────────────

class UserInitRequest(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class QuestSubmitRequest(BaseModel):
    user_id: int
    quest_id: str
    photo: Optional[str] = None   # base64 data URL of homework screenshot


class QuizAnswerRequest(BaseModel):
    user_id: int
    quest_id: str
    question_index: int
    is_correct: bool


class AdminApproveRequest(BaseModel):
    admin_id: int
    user_id: int
    quest_id: str


class AdminRejectRequest(BaseModel):
    admin_id: int
    user_id: int
    quest_id: str
    comment: Optional[str] = "Нужно доработать."
    status: Optional[str] = "rejected"   # "rejected" or "revision"


class ExtendRequest(BaseModel):
    admin_id: int
    user_id: int
    days: int = 2


class PenaltyPaymentRequest(BaseModel):
    user_id: int
    module_index: int
    payment_type: str = "penalty"   # "penalty" or "repurchase"


# ── UTILS ─────────────────────────────────────────────────────────────────────

def _get_admin_ids() -> set:
    raw = os.getenv("ADMIN_ID", "0")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

def check_admin(admin_id: int):
    if admin_id not in _get_admin_ids():
        raise HTTPException(status_code=403, detail="Нет доступа")


def try_advance_module(user_id: int) -> bool:
    state = get_user_state(user_id)
    idx = state["module_index"]
    if idx >= len(MODULES) - 1:
        return False
    module_quests = [q["id"] for q in QUESTS if q["module_index"] == idx]
    completed = set(state["completed_quests"])
    if all(qid in completed for qid in module_quests):
        state["module_index"] += 1
        set_module_deadline(state, hours=DEFAULT_DEADLINE_HOURS)
        save_progress()
        return True
    return False


def build_deadline_info(state: dict) -> dict:
    """Build deadline info dict for API responses."""
    dl = state.get("module_deadline")
    hours_left = get_deadline_hours_remaining(state)
    expired = is_deadline_expired(state)

    info = {
        "deadline": dl.split("T")[0] if dl else None,
        "deadline_iso": dl,
        "hours_remaining": round(hours_left, 2) if hours_left != float("inf") else None,
        "deadline_expired": expired,
        "extensions_used": state.get("deadline_extensions", 0),
        "max_extensions": MAX_EXTENSIONS,
        "can_extend": state.get("deadline_extensions", 0) < MAX_EXTENSIONS,
    }

    if not expired and hours_left != float("inf"):
        if hours_left <= 1:
            info["urgency"] = "critical"   # Red countdown
        elif hours_left <= 6:
            info["urgency"] = "danger"     # Pulsing red
        elif hours_left <= 24:
            info["urgency"] = "warning"    # Orange
        else:
            info["urgency"] = "normal"
    else:
        info["urgency"] = "expired" if expired else "none"

    return info


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "CHM Smart Money Academy API v4.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"ok": True, "users": len(user_progress), "version": "4.0.0"}


# ── USER ──────────────────────────────────────────────────────────────────────

@app.post("/api/user/init")
async def user_init(req: UserInitRequest):
    state = get_user_state(req.user_id)
    name = (
        req.username
        or f"{req.first_name or ''} {req.last_name or ''}".strip()
        or str(req.user_id)
    )
    state["name"] = name

    # Set initial deadline for module 0 (no deadline - free module)
    if state["module_index"] == 0 and not state.get("module_deadline"):
        set_module_deadline(state)

    # Track daily streak
    streak, is_new_day = update_streak(req.user_id)

    # Daily bonus XP
    daily_xp, got_bonus = claim_daily_bonus(req.user_id)

    save_progress()
    return {
        "ok": True,
        "state": state,
        "streak": streak,
        "is_new_day": is_new_day,
        "daily_bonus_xp": daily_xp if got_bonus else 0,
    }


def _state_safe(state: dict) -> dict:
    """Return state without large binary fields."""
    return {k: v for k, v in state.items() if k != "homework_photo"}


@app.get("/api/user/{user_id}")
async def get_user(user_id: int):
    state = get_user_state(user_id)
    return _state_safe(state)


@app.get("/api/user/{user_id}/full")
async def get_user_full(user_id: int):
    """Full user state with computed deadline info."""
    state = get_user_state(user_id)
    result = _state_safe(state)
    result["deadline_info"] = build_deadline_info(state)
    result["next_level_xp"] = None
    current_xp = state.get("xp", 0)
    for threshold, _lvl, _name in SMC_LEVELS:
        if threshold > current_xp:
            result["next_level_xp"] = threshold
            break
    return result


# ── MODULES & LESSONS ────────────────────────────────────────────────────────

@app.get("/api/modules")
async def get_modules():
    return {"modules": MODULES}


@app.get("/api/lessons/meta")
async def lessons_meta():
    data = {k: {"title": v.get("title", k), "text": v.get("text", "")} for k, v in LESSONS.items()}
    return JSONResponse(data)


@app.get("/api/lesson/{lesson_key}")
async def get_lesson(lesson_key: str):
    lesson = LESSONS.get(lesson_key)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return {
        "key": lesson_key,
        "title": lesson["title"],
        "text": lesson["text"],
        "article": lesson["article"],
        "video": lesson.get("video", ""),
    }


# ── CHARTS ───────────────────────────────────────────────────────────────────

@app.get("/api/chart/{lesson_key}")
async def get_chart(lesson_key: str):
    buf = generate_chart(lesson_key)
    if buf is None:
        raise HTTPException(status_code=404, detail="График не найден")
    img_b64 = base64.b64encode(buf.read()).decode()
    return {"image_base64": img_b64, "mime": "image/png"}


@app.get("/api/chart/{lesson_key}/png")
async def get_chart_png(lesson_key: str):
    buf = generate_chart(lesson_key)
    if buf is None:
        raise HTTPException(status_code=404, detail="График не найден")
    return Response(content=buf.read(), media_type="image/png")


# ── QUESTS & QUIZZES ─────────────────────────────────────────────────────────

@app.get("/api/quests/{user_id}")
async def get_quests(user_id: int):
    state = get_user_state(user_id)
    idx = state["module_index"]
    completed = set(state["completed_quests"])
    module_quests = [q for q in QUESTS if q["module_index"] == idx]
    result = [
        {
            "id": q["id"],
            "title": q["title"],
            "type": q["type"],
            "xp_reward": q["xp_reward"],
            "description": q.get("description", ""),
            "completed": q["id"] in completed,
            "is_active": state.get("active_quest") == q["id"],
        }
        for q in module_quests
    ]

    dl_info = build_deadline_info(state)

    return {
        "quests": result,
        "module_index": idx,
        "module_title": MODULES[idx]["title"] if idx < len(MODULES) else "Завершено",
        "module_subtitle": MODULES[idx].get("subtitle", "") if idx < len(MODULES) else "",
        "deadline_expired": dl_info["deadline_expired"],
        "deadline": dl_info["deadline"],
        "deadline_info": dl_info,
        "completed_count": len([q for q in result if q["completed"]]),
        "total_count": len(result),
    }


@app.post("/api/quest/start")
async def start_quest(req: QuestSubmitRequest):
    state = get_user_state(req.user_id)
    if is_deadline_expired(state):
        return {
            "ok": False,
            "error": "deadline_expired",
            "message": "Дедлайн истёк. Оплати штраф для продолжения.",
            "penalty_amount": MODULE_PENALTIES.get(state["module_index"], 5),
            "can_extend": state.get("deadline_extensions", 0) < MAX_EXTENSIONS,
        }

    quest = next((q for q in QUESTS if q["id"] == req.quest_id), None)
    if not quest:
        raise HTTPException(status_code=404, detail="Квест не найден")
    if req.quest_id in state["completed_quests"]:
        return {"ok": False, "error": "already_completed"}

    state["active_quest"] = req.quest_id
    save_progress()

    response = {"ok": True, "quest": quest}

    if quest["type"] == "quiz":
        quiz_id = quest.get("quiz_ref", "")
        quiz_list = QUIZZES.get(quiz_id, [])
        shuffled = []
        for q in quiz_list:
            opts = q["options"].copy()
            random.shuffle(opts)
            shuffled.append({
                "question": q["question"],
                "options": [o[0] for o in opts],
                "correct_index": next(i for i, o in enumerate(opts) if o[1]),
            })
        state["quiz_state"] = {
            "quiz_id": quiz_id,
            "index": 0,
            "correct": 0,
            "total": len(quiz_list),
            "questions": shuffled,
        }
        save_progress()
        response["quiz"] = {"questions": shuffled, "total": len(quiz_list)}

    return response


@app.post("/api/quiz/answer")
async def quiz_answer(req: QuizAnswerRequest):
    state = get_user_state(req.user_id)
    qstate = state.get("quiz_state")
    if not qstate:
        raise HTTPException(status_code=400, detail="Квиз не активен")

    if req.is_correct:
        qstate["correct"] += 1
    qstate["index"] = req.question_index + 1
    state["quiz_state"] = qstate
    save_progress()

    total = qstate["total"]
    current_index = qstate["index"]

    if current_index >= total:
        score = qstate["correct"] / total if total > 0 else 0
        if score >= 0.7:
            quest_id = state.get("active_quest")
            quest = next((q for q in QUESTS if q["id"] == quest_id), None)
            if quest and quest_id not in state["completed_quests"]:
                state["completed_quests"].append(quest_id)
                state["active_quest"] = None
                state["quiz_state"] = None
                level, leveled_up = add_xp(req.user_id, quest["xp_reward"])

                # Award "first blood" badge on first quiz
                if len([q for q in state["completed_quests"] if "quiz" in q]) == 1:
                    award_badge(req.user_id, "first_blood")

                advanced = try_advance_module(req.user_id)
                save_progress()
                return {
                    "ok": True, "finished": True, "passed": True,
                    "score": round(score * 100), "correct": qstate["correct"], "total": total,
                    "xp_earned": quest["xp_reward"],
                    "new_level": level, "leveled_up": leveled_up,
                    "module_advanced": advanced,
                    "rank": get_user_state(req.user_id)["rank"],
                }
        else:
            state["quiz_state"] = None
            state["active_quest"] = None
            save_progress()
            return {
                "ok": True, "finished": True, "passed": False,
                "score": round(score * 100), "correct": qstate["correct"], "total": total,
                "required": 70,
            }

    return {"ok": True, "finished": False, "next_index": current_index}


@app.post("/api/quest/submit")
async def submit_task(req: QuestSubmitRequest):
    state = get_user_state(req.user_id)
    if is_deadline_expired(state):
        return {
            "ok": False,
            "error": "deadline_expired",
            "penalty_amount": MODULE_PENALTIES.get(state["module_index"], 5),
            "can_extend": state.get("deadline_extensions", 0) < MAX_EXTENSIONS,
        }

    # Check if submitted within first 12 hours → "time is money" badge
    dl = state.get("module_deadline")
    if dl:
        try:
            deadline_dt = datetime.fromisoformat(dl)
            hours_used = DEFAULT_DEADLINE_HOURS - (deadline_dt - datetime.utcnow()).total_seconds() / 3600
            if hours_used <= 12:
                award_badge(req.user_id, "time_is_money")
        except Exception:
            pass

    state["active_quest"] = req.quest_id
    state["homework_status"] = "pending"
    state["homework_comment"] = ""
    if req.photo:
        # Store only the first 500KB worth of base64 to prevent bloat
        state["homework_photo"] = req.photo[:700_000]
    save_progress()
    return {
        "ok": True,
        "message": "Задание принято на проверку. Преподаватель проверит в течение 24 часов.",
    }


# ── DEADLINE PENALTY PAYMENT ──────────────────────────────────────────────────

@app.post("/api/deadline/penalty")
async def pay_deadline_penalty(req: PenaltyPaymentRequest):
    """
    Process deadline penalty payment.
    In production: integrate with payment gateway before calling this.
    payment_type: 'penalty' = first miss, 48h extension
                  'repurchase' = second miss, full module repurchase
    """
    state = get_user_state(req.user_id)

    if req.payment_type == "penalty":
        if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
            return {
                "ok": False,
                "error": "max_extensions_reached",
                "message": "Лимит продлений исчерпан. Требуется полная перепокупка модуля.",
                "repurchase_amount": MODULE_FULL_REPURCHASE.get(req.module_index, 15),
            }

        success = apply_penalty_extension(state)
        if success:
            save_progress()
            new_dl = state.get("module_deadline")
            dl_info = build_deadline_info(state)
            return {
                "ok": True,
                "message": "Штраф оплачен. У тебя есть 48 часов. Рынок не прощает промедления.",
                "new_deadline_iso": new_dl,
                "deadline_info": dl_info,
                "extensions_remaining": MAX_EXTENSIONS - state.get("deadline_extensions", 0),
            }
        return {"ok": False, "error": "extension_failed"}

    elif req.payment_type == "repurchase":
        # Full repurchase: reset module progress, set fresh 72h deadline
        module_idx = state["module_index"]
        # Remove all quests for this module from completed
        module_quest_ids = {q["id"] for q in QUESTS if q["module_index"] == module_idx}
        state["completed_quests"] = [
            qid for qid in state["completed_quests"] if qid not in module_quest_ids
        ]
        state["homework_status"] = "idle"
        state["active_quest"] = None
        state["deadline_extensions"] = 0
        set_module_deadline(state, hours=DEFAULT_DEADLINE_HOURS)
        save_progress()
        return {
            "ok": True,
            "message": "Модуль перекуплен. Новый дедлайн: 72 часа. Не повторяй ошибку.",
            "deadline_info": build_deadline_info(state),
        }

    raise HTTPException(status_code=400, detail="Неизвестный тип оплаты")


@app.get("/api/deadline/status/{user_id}")
async def get_deadline_status(user_id: int):
    state = get_user_state(user_id)
    info = build_deadline_info(state)
    info["module_index"] = state["module_index"]
    info["penalty_amount"] = MODULE_PENALTIES.get(state["module_index"], 5)
    info["repurchase_amount"] = MODULE_FULL_REPURCHASE.get(state["module_index"], 15)
    return info


# ── DAILY BONUS ───────────────────────────────────────────────────────────────

@app.post("/api/user/daily-bonus")
async def daily_bonus_endpoint(user_id: int):
    xp, got_bonus = claim_daily_bonus(user_id)
    streak, _ = update_streak(user_id)
    if got_bonus:
        return {"ok": True, "xp_earned": xp, "streak": streak}
    return {"ok": False, "message": "Бонус уже получен сегодня", "streak": streak}


# ── LEADERBOARD & STATS ──────────────────────────────────────────────────────

@app.get("/api/leaderboard")
async def leaderboard(limit: int = Query(default=10, ge=1, le=50)):
    board = get_leaderboard(limit)
    return {"leaderboard": board}


@app.get("/api/stats/{user_id}")
async def user_stats(user_id: int):
    state = get_user_state(user_id)
    idx = state["module_index"]
    module_title = MODULES[idx]["title"] if idx < len(MODULES) else "Завершено"
    dl_info = build_deadline_info(state)
    all_module_quests = [q for q in QUESTS if q["module_index"] == idx]
    completed_module = sum(1 for q in all_module_quests if q["id"] in state["completed_quests"])

    return {
        "name": state.get("name", str(user_id)),
        "level": state["level"], "xp": state["xp"], "rank": state["rank"],
        "module_index": idx, "module_title": module_title,
        "total_quests_completed": len(state["completed_quests"]),
        "module_quests_completed": completed_module,
        "module_quests_total": len(all_module_quests),
        "streak": state.get("streak", 0),
        "badges": state.get("badges", []),
        "deadline_info": dl_info,
        "is_expired": dl_info["deadline_expired"],
    }


# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.post("/api/admin/approve")
async def admin_approve(req: AdminApproveRequest):
    check_admin(req.admin_id)
    state = get_user_state(req.user_id)
    quest = next((q for q in QUESTS if q["id"] == req.quest_id), None)
    if not quest:
        raise HTTPException(status_code=404, detail="Квест не найден")
    if req.quest_id not in state["completed_quests"]:
        state["completed_quests"].append(req.quest_id)
    state["active_quest"] = None
    state["homework_status"] = "approved"
    level, leveled_up = add_xp(req.user_id, quest["xp_reward"])

    # Award "disciplined" badge if homework submitted on time
    if not is_deadline_expired(state) and state.get("module_deadline"):
        award_badge(req.user_id, "disciplined")

    advanced = False
    if req.quest_id.endswith("_boss"):
        advanced = try_advance_module(req.user_id)

    # Check if all modules completed → CHM Legend badge
    if state["module_index"] >= len(MODULES) - 1:
        all_done = all(q["id"] in state["completed_quests"] for q in QUESTS)
        if all_done:
            award_badge(req.user_id, "chm_legend")

    save_progress()
    return {"ok": True, "new_level": level, "leveled_up": leveled_up, "module_advanced": advanced}


@app.post("/api/admin/reject")
async def admin_reject(req: AdminRejectRequest):
    check_admin(req.admin_id)
    state = get_user_state(req.user_id)
    # "revision" = needs correction + resubmit; "rejected" = serious errors
    state["homework_status"] = req.status if req.status in ("rejected", "revision") else "rejected"
    state["homework_comment"] = req.comment or ""
    save_progress()
    return {"ok": True, "comment": req.comment, "status": state["homework_status"]}


@app.post("/api/admin/extend")
async def admin_extend(req: ExtendRequest):
    check_admin(req.admin_id)
    state = get_user_state(req.user_id)
    now = datetime.utcnow()
    dl = state.get("module_deadline")
    try:
        base = datetime.fromisoformat(dl) if dl else now
    except Exception:
        base = now
    new_dl = base + timedelta(days=req.days)
    state["module_deadline"] = new_dl.isoformat()
    # Admin extension doesn't count against MAX_EXTENSIONS
    save_progress()
    return {"ok": True, "new_deadline": new_dl.date().isoformat()}


@app.get("/api/admin/users")
async def admin_users(admin_id: int):
    check_admin(admin_id)
    result = [
        {
            "user_id": uid,
            "name": st.get("name", str(uid)),
            "level": st.get("level", 1), "xp": st.get("xp", 0),
            "rank": st.get("rank", "Наблюдатель рынка"),
            "module_index": st.get("module_index", 0),
            "homework_status": st.get("homework_status", "idle"),
            "homework_comment": st.get("homework_comment", ""),
            "has_photo": bool(st.get("homework_photo")),
            "active_quest": st.get("active_quest"),
            "streak": st.get("streak", 0),
            "badges": st.get("badges", []),
            "is_expired": is_deadline_expired(st),
            "hours_remaining": round(get_deadline_hours_remaining(st), 1),
        }
        for uid, st in user_progress.items()
    ]
    return {"users": result}


@app.get("/api/admin/homework_photo/{user_id}")
async def get_homework_photo(user_id: int, admin_id: int):
    """Return the homework photo submitted by a user (admin only)."""
    check_admin(admin_id)
    st = get_user_state(user_id)
    photo = st.get("homework_photo")
    if not photo:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return {"photo": photo}


# ── WEBHOOK ───────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        process_update(data)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    load_progress()
    logger.info(f"Progress loaded: {len(user_progress)} users")
    if os.getenv("WEBHOOK_URL"):
        setup_webhook()
    else:
        logger.info("WEBHOOK_URL not set — webhook not configured (polling mode)")

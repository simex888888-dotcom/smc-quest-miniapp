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
    user_progress, load_progress, MAX_EXTENSIONS,
)
from lessons import LESSONS, MODULES
from quests import QUESTS, QUIZZES
from charts import generate_chart
from bot import bot as telegram_bot, setup_webhook, process_update

app = FastAPI(title="SMC Quest API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Статика (frontend папка рядом с main.py) ──────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info(f"Фронтенд: {FRONTEND_DIR}")
else:
    logger.warning(f"Папка frontend не найдена: {FRONTEND_DIR}")


# ── MODELS ────────────────────────────────────────────────────────────────────

class UserInitRequest(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class QuestSubmitRequest(BaseModel):
    user_id: int
    quest_id: str


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


class ExtendRequest(BaseModel):
    admin_id: int
    user_id: int
    days: int = 7


# ── UTILS ─────────────────────────────────────────────────────────────────────

def check_admin(admin_id: int):
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if admin_id != ADMIN_ID:
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
        set_module_deadline(state)
        save_progress()
        return True
    return False


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "SMC Quest API v3.0 running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"ok": True, "users": len(user_progress)}


# ── USER ──

@app.post("/api/user/init")
async def user_init(req: UserInitRequest):
    state = get_user_state(req.user_id)
    name = (
        req.username
        or f"{req.first_name or ''} {req.last_name or ''}".strip()
        or str(req.user_id)
    )
    state["name"] = name
    if state["module_index"] == 0 and not state.get("module_deadline"):
        set_module_deadline(state)
    save_progress()
    return {"ok": True, "state": state}


@app.get("/api/user/{user_id}")
async def get_user(user_id: int):
    return get_user_state(user_id)


# ── MODULES & LESSONS ──

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


# ── CHARTS ──

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


# ── QUESTS & QUIZZES ──

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
    deadline_expired = is_deadline_expired(state)
    dl = state.get("module_deadline", "")
    return {
        "quests": result,
        "module_index": idx,
        "module_title": MODULES[idx]["title"] if idx < len(MODULES) else "Завершено",
        "deadline_expired": deadline_expired,
        "deadline": dl.split("T")[0] if dl else None,
        "completed_count": len([q for q in result if q["completed"]]),
        "total_count": len(result),
    }


@app.post("/api/quest/start")
async def start_quest(req: QuestSubmitRequest):
    state = get_user_state(req.user_id)
    if is_deadline_expired(state):
        reset_user_progress(req.user_id)
        return {"ok": False, "error": "deadline_expired", "message": "Дедлайн истёк, прогресс сброшен."}

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
                advanced = try_advance_module(req.user_id)
                save_progress()
                return {
                    "ok": True, "finished": True, "passed": True,
                    "score": round(score * 100), "correct": qstate["correct"], "total": total,
                    "xp_earned": quest["xp_reward"],
                    "new_level": level, "leveled_up": leveled_up,
                    "module_advanced": advanced,
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
        reset_user_progress(req.user_id)
        return {"ok": False, "error": "deadline_expired"}
    state["active_quest"] = req.quest_id
    state["homework_status"] = "pending"
    save_progress()
    return {"ok": True, "message": "Задание принято на проверку. Ждите одобрения администратора."}


# ── LEADERBOARD & STATS ──

@app.get("/api/leaderboard")
async def leaderboard(limit: int = Query(default=10, ge=1, le=50)):
    board = get_leaderboard(limit)
    return {"leaderboard": board}


@app.get("/api/stats/{user_id}")
async def user_stats(user_id: int):
    state = get_user_state(user_id)
    idx = state["module_index"]
    module_title = MODULES[idx]["title"] if idx < len(MODULES) else "Завершено"
    dl = state.get("module_deadline")
    dl_text = dl.split("T")[0] if dl else "не установлен"
    all_module_quests = [q for q in QUESTS if q["module_index"] == idx]
    completed_module = sum(1 for q in all_module_quests if q["id"] in state["completed_quests"])
    return {
        "name": state.get("name", str(user_id)),
        "level": state["level"], "xp": state["xp"], "rank": state["rank"],
        "module_index": idx, "module_title": module_title,
        "total_quests_completed": len(state["completed_quests"]),
        "module_quests_completed": completed_module,
        "module_quests_total": len(all_module_quests),
        "deadline": dl_text, "deadline_extensions": state.get("deadline_extensions", 0),
        "max_extensions": MAX_EXTENSIONS, "is_expired": is_deadline_expired(state),
    }


# ── ADMIN ──

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
    advanced = False
    if req.quest_id.endswith("_boss"):
        advanced = try_advance_module(req.user_id)
    save_progress()
    return {"ok": True, "new_level": level, "leveled_up": leveled_up, "module_advanced": advanced}


@app.post("/api/admin/reject")
async def admin_reject(req: AdminRejectRequest):
    check_admin(req.admin_id)
    state = get_user_state(req.user_id)
    state["homework_status"] = "rejected"
    save_progress()
    return {"ok": True, "comment": req.comment}


@app.post("/api/admin/extend")
async def admin_extend(req: ExtendRequest):
    check_admin(req.admin_id)
    state = get_user_state(req.user_id)
    if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
        return {"ok": False, "error": "Лимит продлений исчерпан"}
    now = datetime.utcnow()
    dl = state.get("module_deadline")
    try:
        base = datetime.fromisoformat(dl) if dl else now
    except Exception:
        base = now
    new_dl = base + timedelta(days=req.days)
    state["module_deadline"] = new_dl.isoformat()
    state["deadline_extensions"] = state.get("deadline_extensions", 0) + 1
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
            "module_index": st.get("module_index", 0),
            "homework_status": st.get("homework_status", "idle"),
            "active_quest": st.get("active_quest"),
        }
        for uid, st in user_progress.items()
    ]
    return {"users": result}


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
    logger.info(f"Прогресс загружен: {len(user_progress)} пользователей")
    if os.getenv("WEBHOOK_URL"):
        setup_webhook()
    else:
        logger.info("WEBHOOK_URL не задан — вебхук не установлен (polling режим)")

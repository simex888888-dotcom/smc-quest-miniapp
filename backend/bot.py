import os
import logging
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

MINIAPP_URL = f"{WEBHOOK_URL}/static/index.html"


def make_main_keyboard(user_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "🚀 Открыть SMC Quest",
            web_app=types.WebAppInfo(url=MINIAPP_URL)
        )
    )
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    user = message.from_user
    bot.reply_to(
        message,
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Добро пожаловать в *SMC Trading Quest* 🏆\n\n"
        "Это VIP-курс по Smart Money Concepts с:\n"
        "📚 20 уроками с графиками\n"
        "⚔️ Квестами и квизами\n"
        "🏅 Лидербордом и XP системой\n"
        "⏰ Дедлайнами по модулям\n\n"
        "Нажми кнопку ниже чтобы начать!",
        reply_markup=make_main_keyboard(user.id)
    )


@bot.message_handler(commands=["app"])
def cmd_app(message: types.Message):
    bot.reply_to(
        message,
        "📱 Открой Mini App:",
        reply_markup=make_main_keyboard(message.from_user.id)
    )


@bot.message_handler(commands=["top"])
def cmd_top(message: types.Message):
    import httpx
    try:
        resp = httpx.get(f"http://localhost:8000/api/leaderboard?limit=10")
        data = resp.json()
        lines = ["🏆 *Лидерборд курса:*\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(data["leaderboard"], start=1):
            medal = medals[i-1] if i <= 3 else f"{i})"
            lines.append(f"{medal} {p['name']} — lvl {p['level']} | {p['xp']} XP")
        bot.reply_to(message, "\n".join(lines))
    except Exception as e:
        bot.reply_to(message, "Ошибка получения лидерборда.")


@bot.message_handler(commands=["stats"])
def cmd_stats(message: types.Message):
    import httpx
    uid = message.from_user.id
    try:
        resp = httpx.get(f"http://localhost:8000/api/stats/{uid}")
        st = resp.json()
        dl_text = st.get("deadline", "не установлен")
        expired_text = " ⚠️ ПРОСРОЧЕН!" if st.get("is_expired") else ""
        bot.reply_to(
            message,
            f"📊 *Твоя статистика:*\n\n"
            f"👤 {st['name']}\n"
            f"⭐ Уровень: {st['level']} | XP: {st['xp']}\n"
            f"🏅 Звание: {st['rank']}\n"
            f"📦 Модуль: {st['module_index']+1} — {st['module_title']}\n"
            f"✅ Квестов: {st['total_quests_completed']}\n"
            f"📅 Дедлайн: {dl_text}{expired_text}"
        )
    except Exception:
        bot.reply_to(message, "Ошибка получения статистики.")


@bot.message_handler(commands=["extend"])
def cmd_extend(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    import httpx
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /extend user_id дни")
        return
    uid, days = int(args[0]), int(args[1])
    resp = httpx.post(
        "http://localhost:8000/api/admin/extend",
        json={"admin_id": ADMIN_ID, "user_id": uid, "days": days}
    )
    data = resp.json()
    if data.get("ok"):
        bot.reply_to(message, f"✅ Дедлайн продлён до {data['new_deadline']}")
        bot.send_message(uid, f"📅 Твой дедлайн продлён на {days} дн. Новый: {data['new_deadline']}")
    else:
        bot.reply_to(message, f"❌ {data.get('error', 'Ошибка')}")


@bot.message_handler(commands=["approve"])
def cmd_approve(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    import httpx
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /approve user_id quest_id")
        return
    uid, quest_id = int(args[0]), args[1]
    resp = httpx.post(
        "http://localhost:8000/api/admin/approve",
        json={"admin_id": ADMIN_ID, "user_id": uid, "quest_id": quest_id}
    )
    data = resp.json()
    if data.get("ok"):
        bot.send_message(uid, f"✅ Квест принят! Модуль {'разблокирован!' if data.get('module_advanced') else 'продолжается.'}")
        bot.reply_to(message, "✅ Квест засчитан.")
    else:
        bot.reply_to(message, "❌ Ошибка")


@bot.message_handler(commands=["reject"])
def cmd_reject(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    import httpx
    args = message.text.split(None, 3)[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /reject user_id quest_id [комментарий]")
        return
    uid, quest_id = int(args[0]), args[1]
    comment = args[2] if len(args) > 2 else "Нужно доработать."
    httpx.post(
        "http://localhost:8000/api/admin/reject",
        json={"admin_id": ADMIN_ID, "user_id": uid, "quest_id": quest_id, "comment": comment}
    )
    bot.send_message(uid, f"❌ Задание отклонено.\nКомментарий: {comment}")
    bot.reply_to(message, "Задание отклонено.")


def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set: {WEBHOOK_URL}/webhook")


def process_update(update_dict: dict):
    update = telebot.types.Update.de_json(update_dict)
    bot.process_new_updates([update])

# ── Webhook endpoint для бота ──
from bot import bot as telegram_bot, setup_webhook, process_update
from fastapi import Request

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    process_update(data)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    load_progress()
    if os.getenv("WEBHOOK_URL"):
        setup_webhook()

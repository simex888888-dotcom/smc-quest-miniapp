import os
import logging
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")   # https://smc-quest-miniapp.onrender.com
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

MINIAPP_URL = f"{WEBHOOK_URL}/static/index.html" if WEBHOOK_URL else ""


def make_main_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    if MINIAPP_URL:
        kb.add(
            types.InlineKeyboardButton(
                "🚀 Открыть SMC Quest",
                web_app=types.WebAppInfo(url=MINIAPP_URL),
            )
        )
    else:
        kb.add(types.InlineKeyboardButton("ℹ️ Бот не настроен", callback_data="noop"))
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    user = message.from_user
    bot.reply_to(
        message,
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Добро пожаловать в *SMC Trading Quest* 🏆\n\n"
        "Это курс по Smart Money Concepts с:\n"
        "📚 20 уроками с графиками\n"
        "⚔️ Квестами и квизами\n"
        "🏅 Лидербордом и XP системой\n"
        "⏰ Дедлайнами по модулям\n\n"
        "Нажми кнопку ниже чтобы начать!",
        reply_markup=make_main_keyboard(),
    )


@bot.message_handler(commands=["app"])
def cmd_app(message: types.Message):
    bot.reply_to(message, "📱 Открой Mini App:", reply_markup=make_main_keyboard())


@bot.message_handler(commands=["top"])
def cmd_top(message: types.Message):
    # Импортируем progress напрямую — нет localhost вызовов
    from progress import get_leaderboard
    try:
        board = get_leaderboard(10)
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 *Лидерборд курса:*\n"]
        for i, p in enumerate(board, start=1):
            medal = medals[i - 1] if i <= 3 else f"{i})"
            lines.append(f"{medal} {p['name']} — lvl {p['level']} | {p['xp']} XP")
        bot.reply_to(message, "\n".join(lines))
    except Exception as e:
        logger.error(f"top error: {e}")
        bot.reply_to(message, "Ошибка получения лидерборда.")


@bot.message_handler(commands=["stats"])
def cmd_stats(message: types.Message):
    from progress import get_user_state, is_deadline_expired
    from lessons import MODULES
    from quests import QUESTS
    uid = message.from_user.id
    try:
        st = get_user_state(uid)
        idx = st.get("module_index", 0)
        dl = st.get("module_deadline", "")
        dl_text = dl.split("T")[0] if dl else "не установлен"
        expired = " ⚠️ ПРОСРОЧЕН!" if is_deadline_expired(st) else ""
        mod_title = MODULES[idx]["title"] if idx < len(MODULES) else "Завершено"
        bot.reply_to(
            message,
            f"📊 *Твоя статистика:*\n\n"
            f"👤 {st.get('name', str(uid))}\n"
            f"⭐ Уровень: {st['level']} | XP: {st['xp']}\n"
            f"🏅 Звание: {st['rank']}\n"
            f"📦 Модуль: {idx + 1} — {mod_title}\n"
            f"✅ Квестов: {len(st.get('completed_quests', []))}\n"
            f"📅 Дедлайн: {dl_text}{expired}",
        )
    except Exception as e:
        logger.error(f"stats error: {e}")
        bot.reply_to(message, "Ошибка получения статистики.")


@bot.message_handler(commands=["extend"])
def cmd_extend(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    from progress import get_user_state, save_progress
    from datetime import datetime, timedelta
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /extend user_id дни"); return
    try:
        uid, days = int(args[0]), int(args[1])
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат"); return
    from progress import MAX_EXTENSIONS
    state = get_user_state(uid)
    if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
        bot.reply_to(message, "❌ Лимит продлений исчерпан"); return
    now = datetime.utcnow()
    dl = state.get("module_deadline")
    base = datetime.fromisoformat(dl) if dl else now
    new_dl = base + timedelta(days=days)
    state["module_deadline"] = new_dl.isoformat()
    state["deadline_extensions"] = state.get("deadline_extensions", 0) + 1
    save_progress()
    new_date = new_dl.date().isoformat()
    bot.reply_to(message, f"✅ Дедлайн продлён до {new_date}")
    try:
        bot.send_message(uid, f"📅 Твой дедлайн продлён на {days} дн. Новый: {new_date}")
    except Exception:
        pass


@bot.message_handler(commands=["approve"])
def cmd_approve(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    from progress import get_user_state, save_progress, add_xp, set_module_deadline
    from quests import QUESTS
    from lessons import MODULES
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /approve user_id quest_id"); return
    uid, quest_id = int(args[0]), args[1]
    state = get_user_state(uid)
    quest = next((q for q in QUESTS if q["id"] == quest_id), None)
    if not quest:
        bot.reply_to(message, "❌ Квест не найден"); return
    if quest_id not in state["completed_quests"]:
        state["completed_quests"].append(quest_id)
    state["active_quest"] = None
    state["homework_status"] = "approved"
    level, leveled_up = add_xp(uid, quest["xp_reward"])
    advanced = False
    if quest_id.endswith("_boss"):
        idx = state["module_index"]
        module_quests = [q["id"] for q in QUESTS if q["module_index"] == idx]
        if all(qid in state["completed_quests"] for qid in module_quests):
            if idx < len(MODULES) - 1:
                state["module_index"] += 1
                set_module_deadline(state)
                advanced = True
    save_progress()
    bot.reply_to(message, "✅ Квест засчитан.")
    notify = "✅ Квест засчитан! "
    notify += "Следующий модуль разблокирован! 🎉" if advanced else "Продолжай!"
    if leveled_up:
        notify += f"\n⬆️ Новый уровень: {level}!"
    try:
        bot.send_message(uid, notify)
    except Exception:
        pass


@bot.message_handler(commands=["reject"])
def cmd_reject(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    from progress import get_user_state, save_progress
    args = message.text.split(None, 3)[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /reject user_id quest_id [комментарий]"); return
    uid, quest_id = int(args[0]), args[1]
    comment = args[2] if len(args) > 2 else "Нужно доработать."
    state = get_user_state(uid)
    state["homework_status"] = "rejected"
    save_progress()
    bot.reply_to(message, "Задание отклонено.")
    try:
        bot.send_message(uid, f"❌ Задание отклонено.\nКомментарий: {comment}")
    except Exception:
        pass


def setup_webhook():
    if not BOT_TOKEN or not WEBHOOK_URL:
        logger.warning("BOT_TOKEN или WEBHOOK_URL не установлены, вебхук не настроен")
        return
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"Вебхук установлен: {WEBHOOK_URL}/webhook")
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")


def process_update(update_dict: dict):
    try:
        update = telebot.types.Update.de_json(update_dict)
        bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"Ошибка обработки апдейта: {e}")

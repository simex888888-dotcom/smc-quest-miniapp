import os
import logging
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

def _admin_ids() -> set:
    raw = os.getenv("ADMIN_ID", "0")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

def is_admin(uid: int) -> bool:
    return uid in _admin_ids()

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

MINIAPP_URL = f"{WEBHOOK_URL}/static/index.html" if WEBHOOK_URL else ""


def make_main_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    if MINIAPP_URL:
        kb.add(
            types.InlineKeyboardButton(
                "🚀 Открыть CHM Smart Money Academy",
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
        "Добро пожаловать в *CHM Smart Money Academy* 🏆\n\n"
        "Здесь ты научишься торговать как Smart Money — крупные институциональные игроки.\n\n"
        "*Что тебя ждёт:*\n"
        "📚 10 модулей с реальными графиками BTC/ETH\n"
        "⚔️ Квесты, квизы и задания на разметку\n"
        "⏰ Дедлайны как на реальном рынке — 72 часа на модуль\n"
        "🏅 7 уровней трейдера: от Наблюдателя до Архитектора рынка\n"
        "🏆 CHM Smart Money Certificate после прохождения\n\n"
        "_Биткоин не ждал тебя в 2017. Не будет ждать и сейчас._\n\n"
        "Нажми кнопку ниже и начни — Модуль 1 бесплатно:",
        reply_markup=make_main_keyboard(),
    )


@bot.message_handler(commands=["app"])
def cmd_app(message: types.Message):
    bot.reply_to(
        message,
        "📱 *CHM Smart Money Academy*\nОткрой и продолжай обучение:",
        reply_markup=make_main_keyboard(),
    )


@bot.message_handler(commands=["top"])
def cmd_top(message: types.Message):
    from progress import get_leaderboard
    try:
        board = get_leaderboard(10)
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 *Лидерборд CHM Academy:*\n"]
        for i, p in enumerate(board, start=1):
            medal = medals[i - 1] if i <= 3 else f"{i})"
            streak_txt = f" 🔥{p['streak']}" if p.get("streak", 0) >= 3 else ""
            lines.append(
                f"{medal} *{p['name']}* — {p['rank']}\n"
                f"   Lvl {p['level']} | {p['xp']} XP | Модуль {p['module']}{streak_txt}"
            )
        bot.reply_to(message, "\n\n".join(lines[:4]) + "\n\n" + "\n".join(lines[4:]))
    except Exception as e:
        logger.error(f"top error: {e}")
        bot.reply_to(message, "Ошибка получения лидерборда.")


@bot.message_handler(commands=["stats"])
def cmd_stats(message: types.Message):
    from progress import get_user_state, is_deadline_expired, get_deadline_hours_remaining
    from lessons import MODULES
    uid = message.from_user.id
    try:
        st = get_user_state(uid)
        idx = st.get("module_index", 0)
        mod_title = MODULES[idx]["title"] if idx < len(MODULES) else "Завершено"
        hours_left = get_deadline_hours_remaining(st)
        expired = is_deadline_expired(st)
        streak = st.get("streak", 0)
        badges = st.get("badges", [])

        if expired:
            dl_text = "⚠️ ПРОСРОЧЕН — оплати штраф!"
        elif hours_left == float("inf"):
            dl_text = "Нет (свободный модуль)"
        elif hours_left <= 1:
            mins = int(hours_left * 60)
            dl_text = f"🔴 КРИТИЧНО: {mins} минут!"
        elif hours_left <= 6:
            dl_text = f"🟠 {hours_left:.1f} часов — торопись!"
        elif hours_left <= 24:
            dl_text = f"🟡 {hours_left:.1f} часов"
        else:
            dl_text = f"🟢 {hours_left:.0f} часов"

        streak_line = f"🔥 Стрик: {streak} дн." if streak > 0 else "Стрик: 0 дней"
        badges_line = f"🏅 Бейджей: {len(badges)}" if badges else "Бейджей: пока нет"

        bot.reply_to(
            message,
            f"📊 *Твоя статистика — CHM Academy:*\n\n"
            f"👤 {st.get('name', str(uid))}\n"
            f"⭐ Уровень: *{st['level']}* — _{st['rank']}_\n"
            f"💎 XP: *{st['xp']}*\n"
            f"📦 Модуль: *{idx + 1}* — {mod_title}\n"
            f"✅ Квестов: {len(st.get('completed_quests', []))}\n"
            f"⏰ Дедлайн: {dl_text}\n"
            f"{streak_line}\n"
            f"{badges_line}",
        )
    except Exception as e:
        logger.error(f"stats error: {e}")
        bot.reply_to(message, "Ошибка получения статистики.")


@bot.message_handler(commands=["deadline"])
def cmd_deadline(message: types.Message):
    """Show deadline info with rhetoric."""
    from progress import get_user_state, is_deadline_expired, get_deadline_hours_remaining
    uid = message.from_user.id
    try:
        st = get_user_state(uid)
        hours_left = get_deadline_hours_remaining(st)
        expired = is_deadline_expired(st)

        if expired:
            bot.reply_to(
                message,
                f"🔴 *Дедлайн истёк.*\n\n"
                f"Именно так рынок закрывает позиции у тех, кто медлит.\n\n"
                f"Открой приложение → оплати штраф → продолжи путь.",
                reply_markup=make_main_keyboard(),
            )
        elif hours_left == float("inf"):
            bot.reply_to(message, "✅ Модуль 1 бесплатный — дедлайн не установлен.")
        elif hours_left <= 1:
            mins = int(hours_left * 60)
            bot.reply_to(
                message,
                f"🚨 *ПОСЛЕДНИЙ ШАС — {mins} МИНУТ!*\n\n"
                "Каждая минута промедления — потерянный сетап.\n"
                "Профессионалы работают по расписанию. Сдавай СЕЙЧАС.",
                reply_markup=make_main_keyboard(),
            )
        elif hours_left <= 6:
            bot.reply_to(
                message,
                f"⚠️ *До дедлайна {hours_left:.1f} часов.*\n\n"
                "Рынок не ждал никого — и мы тоже.\n"
                "Сдай домашку сейчас или готовься платить штраф. Это твой выбор.",
                reply_markup=make_main_keyboard(),
            )
        else:
            bot.reply_to(
                message,
                f"⏰ До дедлайна: *{hours_left:.0f} часов*\n\n"
                "Каждый час промедления — это потерянный сетап на реальном рынке.",
            )
    except Exception as e:
        logger.error(f"deadline error: {e}")
        bot.reply_to(message, "Ошибка.")


@bot.message_handler(commands=["extend"])
def cmd_extend(message: types.Message):
    if not is_admin(message.from_user.id):
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
    state = get_user_state(uid)
    now = datetime.utcnow()
    dl = state.get("module_deadline")
    base = datetime.fromisoformat(dl) if dl else now
    new_dl = base + timedelta(days=days)
    state["module_deadline"] = new_dl.isoformat()
    save_progress()
    new_date = new_dl.date().isoformat()
    bot.reply_to(message, f"✅ Дедлайн продлён до {new_date}")
    try:
        bot.send_message(
            uid,
            f"📅 *Дедлайн продлён на {days} дн.*\n"
            f"Новый дедлайн: {new_date}\n\n"
            "Используй это время с умом. Рынок не будет ждать вечно."
        )
    except Exception:
        pass


@bot.message_handler(commands=["approve"])
def cmd_approve(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    from progress import get_user_state, save_progress, add_xp, set_module_deadline, DEFAULT_DEADLINE_HOURS
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
                set_module_deadline(state, hours=DEFAULT_DEADLINE_HOURS)
                advanced = True
    save_progress()
    bot.reply_to(message, f"✅ Квест {quest_id} засчитан пользователю {uid}.")

    notify = f"✅ *Домашнее задание принято!*\n+{quest['xp_reward']} XP"
    if advanced:
        new_idx = state["module_index"]
        new_mod = MODULES[new_idx]["title"] if new_idx < len(MODULES) else "Завершено"
        notify += (
            f"\n\n🎉 *Модуль {new_idx} разблокирован: {new_mod}*\n"
            f"⏰ Дедлайн: 72 часа\n\n"
            "_Биткоин не ждал тебя в 2017. Не будет ждать и сейчас. Начинай._"
        )
    if leveled_up:
        notify += f"\n⬆️ *Новый уровень: {level}!*\n_{state['rank']}_"
    try:
        bot.send_message(uid, notify, parse_mode="Markdown")
    except Exception:
        pass


@bot.message_handler(commands=["reject"])
def cmd_reject(message: types.Message):
    """Usage: /reject user_id quest_id [комментарий]  → rejected
              /revision user_id quest_id [комментарий] → revision (needs resubmit)"""
    if not is_admin(message.from_user.id):
        return
    from progress import get_user_state, save_progress
    cmd = message.text.split()[0].lstrip("/")   # "reject" or "revision"
    args = message.text.split(None, 3)[1:]
    if len(args) < 2:
        bot.reply_to(message, f"Использование: /{cmd} user_id quest_id [комментарий]"); return
    uid, quest_id = int(args[0]), args[1]
    comment = args[2] if len(args) > 2 else "Нужно доработать."
    status = "revision" if cmd == "revision" else "rejected"
    state = get_user_state(uid)
    state["homework_status"] = status
    save_progress()
    bot.reply_to(message, f"{'🔄 На доработке' if status == 'revision' else '⛔ Отклонено'}.")
    if status == "revision":
        msg = (
            f"🔄 *Нужна доработка домашки*\n\n"
            f"Фидбек:\n_{comment}_\n\n"
            "Исправь разметку и отправь скрин снова. Модуль откроется после принятия."
        )
    else:
        msg = (
            f"⛔ *Домашка не принята*\n\n"
            f"Причина:\n_{comment}_\n\n"
            "Серьёзные ошибки в структуре. Пересмотри уроки и сделай разметку заново."
        )
    try:
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception:
        pass


@bot.message_handler(commands=["revision"])
def cmd_revision(message: types.Message):
    """Alias: /revision → calls cmd_reject with revision status."""
    cmd_reject(message)


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


def notify_deadline_warning(user_id: int, hours_left: float):
    """Send deadline warning notification to user."""
    try:
        if hours_left <= 1:
            mins = int(hours_left * 60)
            bot.send_message(
                user_id,
                f"🚨 *ПОСЛЕДНИЙ ШАС — {mins} МИНУТ!*\n\n"
                "Красный экран. Таймер идёт.\n"
                "Сдавай домашку ПРЯМО СЕЙЧАС пока не заблокировали.",
                reply_markup=make_main_keyboard(),
            )
        elif hours_left <= 6:
            bot.send_message(
                user_id,
                f"⚠️ *До дедлайна {hours_left:.0f} часов. Последний шанс.*\n\n"
                "Рынок не ждал никого — и мы тоже.\n"
                "Сдай домашку сейчас или готовься платить штраф. Это твой выбор.",
                reply_markup=make_main_keyboard(),
            )
        elif hours_left <= 24:
            bot.send_message(
                user_id,
                f"⏰ *Напоминание: до дедлайна {hours_left:.0f} часов.*\n\n"
                "Каждый час промедления — это потерянный сетап на реальном рынке.\n"
                "Профессионалы работают по расписанию. Любители — когда удобно.",
                reply_markup=make_main_keyboard(),
            )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления {user_id}: {e}")


def notify_inactivity(user_id: int, user_name: str):
    """Notify user after 48+ hours of inactivity."""
    try:
        bot.send_message(
            user_id,
            f"Эй, *{user_name}*. Пока ты отдыхал — биткоин сделал несколько сетапов "
            f"по системе, которую ты ещё не изучил.\n\n"
            f"Вернись. Дедлайн тикает. Рынок не будет ждать.",
            reply_markup=make_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления о неактивности {user_id}: {e}")

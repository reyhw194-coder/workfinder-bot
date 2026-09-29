import telebot
from telebot import types
import json
import os
import logging
import html

# ==========================================
# НАСТРОЙКИ
# ==========================================

TOKEN = os.getenv("TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "8610258199").strip())

IPHONE_MANAGER = "@Margoo99"
ANDROID_MANAGER = "@maryanazeml06"

DATABASE_FILE = "users.json"

if not TOKEN or ":" not in TOKEN:
    raise RuntimeError(
        "Не задан правильный TOKEN. Добавьте токен бота "
        "в Variables на Railway."
    )

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
logging.basicConfig(level=logging.INFO)

# Временные данные анкет
users = {}


# ==========================================
# БАЗА
# ==========================================

def load_database():
    if not os.path.exists(DATABASE_FILE):
        return set()

    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return set(str(user_id) for user_id in data)

    except (OSError, json.JSONDecodeError, TypeError):
        logging.exception("Ошибка чтения базы users.json")
        return set()


submitted_users = load_database()


def save_database():
    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            list(submitted_users),
            file,
            ensure_ascii=False,
            indent=2
        )


def already_submitted(cid):
    return str(cid) in submitted_users


# ==========================================
# /START
# ==========================================

@bot.message_handler(commands=["start"])
def start(message):
    cid = message.chat.id

    if cid != OWNER_ID and already_submitted(cid):
        bot.send_message(
            cid,
            "⚠️ <b>Вы уже отправляли заявку.</b>\n\n"
            "Повторная отправка заявки невозможна."
        )
        return

    users[cid] = {}

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "📱 iPhone",
            callback_data="phone_iphone"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🤖 Android",
            callback_data="phone_android"
        )
    )

    bot.send_message(
        cid,
        "🌸 <b>Приветствую!</b>\n\n"
        "Я помощник <b>WorkFinder</b>.\n\n"
        "Чтобы подобрать вам подходящую подработку, "
        "ответьте на несколько вопросов.\n\n"
        "<b>1. Какая у вас модель телефона?</b>",
        reply_markup=kb
    )


# ==========================================
# КНОПКИ
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id
    data = call.data

    if cid != OWNER_ID and already_submitted(cid):
        bot.answer_callback_query(
            call.id,
            "⚠️ Вы уже подавали заявку",
            show_alert=True
        )
        return

    if data.startswith("phone_"):
        phone = (
            "iPhone"
            if data == "phone_iphone"
            else "Android"
        )

        users.setdefault(cid, {})
        users[cid]["phone"] = phone

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "💵 RUB",
                callback_data="cur_RUB"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "💎 USDT",
                callback_data="cur_USDT"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "🇰🇿 KZT",
                callback_data="cur_KZT"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "✍️ Другое",
                callback_data="cur_other"
            )
        )

        bot.edit_message_text(
            "💰 <b>2. В какой валюте вам удобно получать оплату?</b>",
            cid,
            call.message.message_id,
            reply_markup=kb
        )

        bot.answer_callback_query(call.id)
        return

    if data in ("cur_RUB", "cur_USDT", "cur_KZT"):
        users.setdefault(cid, {})["currency"] = (
            data.replace("cur_", "")
        )

        ask_hours(cid, call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    if data == "cur_other":
        users.setdefault(cid, {})["waiting_currency"] = True

        bot.edit_message_text(
            "✍️ <b>Напишите название валюты:</b>",
            cid,
            call.message.message_id
        )

        bot.answer_callback_query(call.id)
        return

    if data in ("hours_2", "hours_3", "hours_5"):
        hours = {
            "hours_2": "2 часа",
            "hours_3": "3 часа",
            "hours_5": "5 часов"
        }[data]

        users.setdefault(cid, {})["hours"] = hours

        bot.answer_callback_query(call.id)
        send_application(cid)
        return

    if data == "hours_other":
        users.setdefault(cid, {})["waiting_hours"] = True

        bot.edit_message_text(
            "✍️ <b>Напишите, сколько часов в день "
            "вы готовы уделять подработке:</b>",
            cid,
            call.message.message_id
        )

        bot.answer_callback_query(call.id)


# ==========================================
# ВЫБОР ЧАСОВ
# ==========================================

def make_hours_keyboard():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "2 часа",
            callback_data="hours_2"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "3 часа",
            callback_data="hours_3"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "5 часов",
            callback_data="hours_5"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "✍️ Другое",
            callback_data="hours_other"
        )
    )

    return kb


def ask_hours(cid, message_id):
    bot.edit_message_text(
        "⏰ <b>3. Сколько часов в день "
        "вы готовы уделять подработке?</b>",
        cid,
        message_id,
        reply_markup=make_hours_keyboard()
    )


def ask_hours_after_text(cid):
    bot.send_message(
        cid,
        "⏰ <b>3. Сколько часов в день "
        "вы готовы уделять подработке?</b>",
        reply_markup=make_hours_keyboard()
    )


# ==========================================
# ТЕКСТОВЫЕ ОТВЕТЫ
# ==========================================

@bot.message_handler(content_types=["text"])
def text_handler(message):
    cid = message.chat.id
    answer = (message.text or "").strip()

    if cid != OWNER_ID and already_submitted(cid):
        bot.send_message(
            cid,
            "⚠️ <b>Вы уже отправляли заявку.</b>\n\n"
            "Повторная отправка невозможна."
        )
        return

    if cid not in users:
        return

    if users[cid].get("waiting_currency"):
        users[cid]["currency"] = answer
        users[cid]["waiting_currency"] = False

        ask_hours_after_text(cid)
        return

    if users[cid].get("waiting_hours"):
        users[cid]["hours"] = answer
        users[cid]["waiting_hours"] = False

        send_application(cid)
        return


# ==========================================
# ОТПРАВКА ЗАЯВКИ
# ==========================================

def send_application(cid):
    if cid not in users:
        return

    data = users[cid]

    phone = data.get("phone", "Не указано")
    currency = data.get("currency", "Не указано")
    hours = data.get("hours", "Не указано")

    try:
        chat = bot.get_chat(cid)

        username = (
            "@" + chat.username
            if chat.username
            else "Username отсутствует"
        )

        full_name = html.escape(
            chat.first_name or "Не указано"
        )

    except Exception:
        username = "Username отсутствует"
        full_name = "Не указано"

    manager = (
        IPHONE_MANAGER
        if phone == "iPhone"
        else ANDROID_MANAGER
    )

    manager_url = (
        "https://t.me/" + manager.lstrip("@")
    )

    application = (
        "📥 <b>НОВАЯ ЗАЯВКА WorkFinder</b>\n\n"
        f"👤 Имя: <b>{full_name}</b>\n"
        f"🔗 Пользователь: <b>{html.escape(username)}</b>\n"
        f"🆔 Telegram ID: <code>{cid}</code>\n\n"
        f"📱 Телефон: <b>{html.escape(phone)}</b>\n"
        f"💰 Валюта: <b>{html.escape(currency)}</b>\n"
        f"⏰ Время: <b>{html.escape(hours)}</b>\n\n"
        f"👨‍💼 Менеджер: <b>{html.escape(manager)}</b>"
    )

    # Сначала отправляем заявку администратору.
    # Не отправляем её менеджеру по username:
    # это могло вызывать ошибку chat not found.

    try:
        bot.send_message(OWNER_ID, application)

    except Exception:
        logging.exception(
            "Не удалось отправить заявку администратору"
        )

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                f"Написать менеджеру {manager}",
                url=manager_url
            )
        )

        bot.send_message(
            cid,
            "⚠️ <b>Не удалось передать заявку администратору.</b>\n\n"
            "Попробуйте связаться с менеджером напрямую.",
            reply_markup=kb
        )

        return

    # Блокируем повторные заявки только после успешной отправки.
    if cid != OWNER_ID:
        submitted_users.add(str(cid))
        save_database()

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            f"Связаться с менеджером {manager}",
            url=manager_url
        )
    )

    bot.send_message(
        cid,
        "✅ <b>Анкета отправлена администратору.</b>\n\n"
        "Спасибо за заполнение анкеты. "
        "Администратор рассмотрит её. "
        "Вы также можете связаться с менеджером "
        "по вашему устройству.",
        reply_markup=kb
    )

    users.pop(cid, None)


# ==========================================
# ЗАПУСК
# ==========================================

print("===================================")
print("WorkFinder bot запущен")
print("===================================")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )

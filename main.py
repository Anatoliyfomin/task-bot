import os
import json
import logging
import telebot
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from telebot import types
from flask import Flask, request, abort, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.environ.get("Telegram_token")
SPREADSHEET_ID = os.environ.get("spreasheet_id")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)
flask_app = Flask(__name__)

ADMINS = [5587445993, 8214573175, 6918277580]

DEADLINE_FORMAT = "%d.%m.%Y"
PREDEFINED_OBJECTS = [
    "Кирпичная",
    "Ольминского",
    "Ярославская",
    "Черницынский",
]

STATUS_CODES = {0: "🔴 Не начато", 1: "🟡 В работе", 2: "🟢 Выполнено"}
STATUS_ICONS = {0: "🔴", 1: "🟡", 2: "🟢"}
STATUS_TO_CODE = {v: k for k, v in STATUS_CODES.items()}

OBJECTS_CACHE: list[str] = []
pending_tasks: dict[int, str] = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def main_menu() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🏢 Объекты", "➕ Новая задача")
    markup.add("🔍 Поиск", "ℹ️ Помощь")
    return markup

# ================= WEBHOOK =================
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    if request.content_type != "application/json":
        abort(403)
    update = types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "", 200

@bot.message_handler(commands=["start"])
def handle_start(message: types.Message) -> None:
    bot.send_message(
        message.chat.id,
        "✅ *Тех Задачи*\n\nВыбери объект для просмотра задач.",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

@bot.message_handler(func=lambda m: True)
def handle_text(message: types.Message) -> None:
    text = message.text
    user_id = message.from_user.id

    if text == "🏢 Объекты":
        show_objects(message)
    elif text == "➕ Новая задача":
        if is_admin(user_id):
            sent = bot.send_message(message.chat.id, "📝 Напишите задачу:")
            bot.register_next_step_handler(sent, ask_object)
        else:
            bot.send_message(message.chat.id, "⛔ Только администраторы могут добавлять задачи.")
    elif text == "🔍 Поиск":
        sent = bot.send_message(message.chat.id, "Что ищем?")
        bot.register_next_step_handler(sent, search_task)
    elif text == "ℹ️ Помощь":
        bot.send_message(
            message.chat.id,
            "🏢 *Объекты* — список объектов с задачами\n"
            "➕ *Новая задача* — добавить задачу (только админы)\n"
            "Задачи проходят: 🔴 Не начато → 🟡 В работе → 🟢 Выполнено",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
    else:
        if is_admin(user_id):
            sent = bot.send_message(message.chat.id, "📝 Напишите задачу:")
            bot.register_next_step_handler(sent, ask_object)
        else:
            bot.send_message(message.chat.id, "⛔ Добавлять задачи могут только администраторы.")

# ================= ОБЪЕКТЫ И ЗАДАЧИ =================
def _refresh_cache() -> list[str]:
    from_sheet = []  # можно добавить sheets.get_objects() если нужно
    merged = list(PREDEFINED_OBJECTS)
    OBJECTS_CACHE.clear()
    OBJECTS_CACHE.extend(merged)
    return merged

def show_objects(message: types.Message, refresh: bool = False) -> None:
    objects = _refresh_cache()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, obj in enumerate(objects):
        markup.add(types.InlineKeyboardButton(f"🏢 {obj}", callback_data=f"vobj_{i}"))
    bot.send_message(message.chat.id, "🏢 *Объекты:*", parse_mode="Markdown", reply_markup=markup)

def ask_object(message: types.Message) -> None:
    task_text = message.text.strip()
    pending_tasks[message.from_user.id] = task_text
    markup = types.InlineKeyboardMarkup(row_width=2)
    for i, obj in enumerate(PREDEFINED_OBJECTS):
        markup.add(types.InlineKeyboardButton(f"🏢 {obj}", callback_data=f"pickobj_{i}"))
    bot.send_message(message.chat.id, f"📝 *{task_text}*\n\n🏢 Выберите объект:", parse_mode="Markdown", reply_markup=markup)

def save_new_task(message: types.Message, task_text: str, obj_name: str) -> None:
    raw = message.text.strip()
    deadline = raw if raw.lower() not in ("нет", "no", "-", "") else ""
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    sheet.append_row([date, task_text, "Не начато", deadline, obj_name])
    bot.send_message(message.chat.id, "✅ Задача добавлена!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: types.CallbackQuery) -> None:
    try:
        parts = call.data.split("_")
        action = parts[0]
        if action == "pickobj":
            obj_idx = int(parts[1])
            user_id = call.from_user.id
            task_text = pending_tasks.pop(user_id, None)
            if not task_text:
                return
            obj_name = PREDEFINED_OBJECTS[obj_idx]
            bot.answer_callback_query(call.id, f"🏢 {obj_name}")
            sent = bot.send_message(call.message.chat.id, "📅 Укажите дедлайн (например: 31.12.2026)\nИли напишите «нет»:", parse_mode="Markdown")
            bot.register_next_step_handler(sent, lambda m: save_new_task(m, task_text, obj_name))
    except Exception as exc:
        logger.error("Callback error: %s", exc)

print("🤖 Бот запущен на Render!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    app.run(host="0.0.0.0", port=port)

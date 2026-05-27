import os
import json
import logging
import telebot
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from telebot import types
from flask import Flask, request

# ================= НАСТРОЙКИ =================
TOKEN = os.environ.get("Telegram_token")
SPREADSHEET_ID = os.environ.get("spreasheet_id")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

ADMINS = [5587445993, 8214573175, 6918277580]   # ← Можно изменить

# Подключение
creds_dict = json.loads(GOOGLE_CREDENTIALS)
creds = Credentials.from_service_account_info(creds_dict)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

PREDEFINED_OBJECTS = ["Кирпичная", "Ольминского", "Ярославская", "Черницынский"]
pending_tasks = {}  # user_id → task_text

def is_admin(user_id):
    return user_id in ADMINS

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🏢 Объекты", "➕ Новая задача")
    markup.add("🔍 Поиск", "ℹ️ Помощь")
    return markup

# ================= WEBHOOK =================
@app.route('/webhook', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
        "✅ *Технические Задачи*\n\nВыбери объект или добавь новую задачу.", 
        parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
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
        bot.send_message(message.chat.id, "Выберите объект для просмотра задач.", reply_markup=main_menu())

def ask_object(message):
    task_text = message.text.strip()
    pending_tasks[message.from_user.id] = task_text
    markup = types.InlineKeyboardMarkup(row_width=2)
    for i, obj in enumerate(PREDEFINED_OBJECTS):
        markup.add(types.InlineKeyboardButton(f"🏢 {obj}", callback_data=f"pickobj_{i}"))
    bot.send_message(message.chat.id, f"📝 *{task_text}*\n\n🏢 Выберите объект:", parse_mode="Markdown", reply_markup=markup)

def save_new_task(message, task_text, obj_name):
    raw = message.text.strip()
    deadline = raw if raw.lower() not in ("нет", "no", "-", "") else ""
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    sheet.append_row([date, task_text, "Не начато", deadline, obj_name])
    bot.send_message(message.chat.id, "✅ Задача добавлена!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
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
    except:
        pass

print("🤖 Бот запущен на Render!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    app.run(host="0.0.0.0", port=port)

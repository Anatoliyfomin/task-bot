import os
import json
import logging
from datetime import datetime
import telebot
from telebot import types
from flask import Flask, request, abort

# ================= НАСТРОЙКИ =================
TOKEN = os.environ.get("Telegram_token")
SPREADSHEET_ID = os.environ.get("spreasheet_id")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

ADMINS = [5587445993, 8214573175, 6918277580]   # ← Замени, если нужно

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к Google Sheets
creds_dict = json.loads(GOOGLE_CREDENTIALS)
creds = Credentials.from_service_account_info(creds_dict)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

PREDEFINED_OBJECTS = [
    "Кирпичная",
    "Ольминского",
    "Ярославская",
    "Черницынский"
]

DEADLINE_FORMAT = "%d.%m.%Y"
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
        "✅ *Тех Задачи*\n\nВыбери объект для просмотра задач.", 
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
    # ... остальные обработчики

print("🤖 Бот запущен на Render!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    app.run(host="0.0.0.0", port=port)

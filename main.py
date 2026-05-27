import os
import json
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

ADMINS = [5587445993, 8214573175, 6918277580]   # ← Замени, если нужно

# Правильные scopes
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

creds_dict = json.loads(GOOGLE_CREDENTIALS)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

PREDEFINED_OBJECTS = ["Кирпичная", "Ольминского", "Ярославская", "Черницынский"]
pending_tasks = {}

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
    bot.send_message(message.chat.id, "✅ Бот запущен!\nВыбери объект или добавь задачу.", reply_markup=main_menu())

# ... (остальные функции: ask_object, save_new_task, callback_handler и т.д.)

print("🤖 Бот запущен на Render!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    app.run(host="0.0.0.0", port=port)

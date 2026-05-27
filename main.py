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

ADMINS = [ВАШ_ID, ВТОРОЙ_ID]   # ← Замени на реальные ID

# Подключение к Google через строку
creds_dict = json.loads(GOOGLE_CREDENTIALS)
creds = Credentials.from_service_account_info(creds_dict)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def is_admin(user_id):
    return user_id in ADMINS

# ================= WEBHOOK =================
@app.route('/webhook', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

# ================= КНОПКИ =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        action, row_num = call.data.split("_")
        row_num = int(row_num)

        if action == "work":
            sheet.update_cell(row_num, 3, "В работе")
            bot.answer_callback_query(call.id, "▶️ Взят в работу!")
        elif action == "done":
            sheet.update_cell(row_num, 3, "Выполнено")
            bot.answer_callback_query(call.id, "✅ Выполнено!")

        show_tasks(call.message, refresh=True)
    except:
        pass

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Мои задачи", "➕ Новая задача")
    markup.add("🔍 Поиск задач", "ℹ️ Помощь")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "✅ Бот запущен!", reply_markup=main_menu())

# ... (добавь сюда остальные функции: show_tasks, add_task и т.д.)

print("🤖 Бот запущен на Render!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    app.run(host="0.0.0.0", port=port)

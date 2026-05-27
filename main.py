import os
import logging
import threading
from pathlib import Path
from datetime import datetime
import telebot
from telebot import types
from flask import Flask, request, abort, jsonify
import sheets

# ================= НАСТРОЙКИ =================
TOKEN = os.environ.get("Telegram_token")           # ← исправлено под твой Secret
SPREADSHEET_ID = os.environ.get("spreasheet_id")   # ← добавлено

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
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

# ... (весь остальной код без изменений) ...

def is_overdue(deadline: str) -> bool:
    if not deadline:
        return False
    try:
        return datetime.strptime(deadline.strip(), DEADLINE_FORMAT).date() < datetime.now().date()
    except ValueError:
        return False

def _send_or_edit(message: types.Message, text: str, markup, refresh: bool) -> None:
    if refresh and hasattr(message, "message_id"):
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=markup,
            )
            return
        except Exception:
            pass
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# Flask endpoints
@flask_app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    if request.content_type != "application/json":
        abort(403)
    update = types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "", 200

# ─── /start ────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def handle_start(message: types.Message) -> None:
    bot.send_message(
        message.chat.id,
        "✅ *Тех Задачи*\n\nВыбери объект для просмотра задач.",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

# (весь остальной код с callback_handler, handle_text, show_objects и т.д. оставлен без изменений)

# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Bot is starting...")
    
    creds_path = Path(__file__).parent / "credentials.json"
    if not creds_path.exists():
        logger.error("Missing credentials.json")
        raise SystemExit(1)

    sheets.ensure_header()

    # Для Render.com используем webhook
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    
    logger.info("Webhook mode active")
    logger.info("Bot is running. Admins: %s", ADMINS)
    
    flask_app.run(host="0.0.0.0", port=port)

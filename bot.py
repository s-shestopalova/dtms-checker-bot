import os
import logging
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# ─── Configuration ───────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")
SERVICE_URL = os.getenv("SERVICE_URL")  # e.g. https://your-service.onrender.com
NAME        = os.getenv("NAME",    "Max")
SURNAME     = os.getenv("SURNAME", "Mustermann")
EMAIL       = os.getenv("EMAIL",   "test@example.com")
PHONE       = os.getenv("PHONE",   "0123456789")
BASE_URL    = "https://dtms.wiesbaden.de/DTMSTerminWeb/"

logging.basicConfig(level=logging.INFO)

# ─── Scraper (requests + BeautifulSoup) ──────────────────────────────────────
def get_appointment_info():
    sess = requests.Session()
    # 1) GET front page to pick up cookies + hidden fields
    r = sess.get(BASE_URL)
    soup = BeautifulSoup(r.text, "html.parser")

    # TODO: extract any hidden form fields here
    # e.g.: token = soup.find("input", {"name":"__RequestVerificationToken"})["value"]

    # 2) POST Fachbereich = Fahrerlaubnisbehörde
    data = {
        # replace "serviceGroup" with the actual field name from the first form
        "serviceGroup": "Fahrerlaubnisbehörde",
        # "__RequestVerificationToken": token,
    }
    r = sess.post(BASE_URL + "step1", data=data)
    soup = BeautifulSoup(r.text, "html.parser")

    # 3) POST personal data
    # TODO: extract new hidden fields from this page if needed
    data = {
        "vorname": NAME,
        "nachname": SURNAME,
        "email": EMAIL,
        "telefon": PHONE,
        "datenschutz": "on",
        # "__RequestVerificationToken": new_token,
    }
    r = sess.post(BASE_URL + "step2", data=data)
    soup = BeautifulSoup(r.text, "html.parser")

    # 4) POST “Umschreibung ausländischer Führerschein” = 1
    data = {
        # replace "umschreibungField" with the actual field name
        "umschreibungField": "1",
        # "__RequestVerificationToken": new_token2,
    }
    r = sess.post(BASE_URL + "step3", data=data)
    soup = BeautifulSoup(r.text, "html.parser")

    # 5) POST to trigger the search
    r = sess.post(BASE_URL + "search", data={})
    soup = BeautifulSoup(r.text, "html.parser")

    # 6) Extract up to 3 appointment slots
    slots = [el.get_text(strip=True) for el in soup.select(".appointment")[:3]]
    return "\n".join(slots) if slots else "Keine Termine gefunden."

# ─── Telegram Bot Setup ──────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, update_queue=None, workers=4, use_context=True)

def cmd_check(update: Update, context):
    try:
        text = get_appointment_info()
    except Exception as e:
        text = f"Fehler beim Abrufen: {e}"
    update.message.reply_text(text)

dispatcher.add_handler(CommandHandler("check", cmd_check))

# optional: log any handler errors
def bot_error(update, context):
    logging.error("Error handling update", exc_info=context.error)

dispatcher.add_error_handler(bot_error)

# ─── Flask & Webhook ──────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    try:
        dispatcher.process_update(update)
    except Exception:
        pass
    return "OK", 200

@app.route("/info")
def info():
    # show Telegram’s idea of your webhook
    return str(bot.get_webhook_info())

if __name__ == "__main__":
    # register webhook
    bot.set_webhook(f"{SERVICE_URL}/webhook")
    # start Flask (no reloader)
    app.run(host="0.0.0.0", port=10000, use_reloader=False)

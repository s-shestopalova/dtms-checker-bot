import os
import logging
from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# ─── Configuration ──────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")
SERVICE_URL = os.getenv("SERVICE_URL")  # e.g. https://your-service.onrender.com
NAME        = os.getenv("NAME",    "Max")
SURNAME     = os.getenv("SURNAME", "Mustermann")
EMAIL       = os.getenv("EMAIL",   "test@example.com")
PHONE       = os.getenv("PHONE",   "0123456789")
URL         = "https://dtms.wiesbaden.de/DTMSTerminWeb/"

# ─── Scraper ──────────────────────────────────────────────────────────────────
def get_appointment_info():
    try:
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=opts)

        driver.get(URL)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Fahrerlaubnisbehörde')]"))
        ).click()

        WebDriverWait(driver, 10).until(lambda d: d.find_element(By.ID, "field-vorname")).send_keys(NAME)
        driver.find_element(By.ID, "field-nachname").send_keys(SURNAME)
        driver.find_element(By.ID, "field-email")  .send_keys(EMAIL)
        driver.find_element(By.ID, "field-telefon").send_keys(PHONE)
        driver.find_element(By.ID, "datenschutz")  .click()
        driver.find_element(By.XPATH, "//button[contains(text(),'Weiter')]").click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h4[contains(text(),'Umschreibung')]"))
        )
        inp = driver.find_element(
            By.XPATH,
            "//h4[contains(text(),'Umschreibung')]/ancestor::div[contains(@class,'leistung')]"
            "/descendant::input[@type='number']"
        )
        inp.clear(); inp.send_keys("1")
        driver.find_element(By.XPATH, "//button[contains(text(),'Weiter')]").click()

        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Suchen')]"))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "appointment"))
        )

        elems = driver.find_elements(By.CLASS_NAME, "appointment")[:3]
        lines = [e.text.strip() for e in elems if e.text.strip()]
        driver.quit()
        return "\n".join(lines) if lines else "Keine Termine gefunden."

    except Exception as e:
        # Catch any scraping errors
        return f"Fehler beim Abrufen: {e}"

# ─── Telegram Setup ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
# Dispatcher with 4 worker threads so it can run handlers in parallel
dispatcher = Dispatcher(bot, update_queue=None, workers=4, use_context=True)

def cmd_check(update: Update, context):
    update.message.reply_text(get_appointment_info())

# Register /check command
dispatcher.add_handler(CommandHandler("check", cmd_check))

# Register a catch-all error handler so exceptions are logged, not swallowed
def bot_error(update, context):
    logging.error("Error handling update", exc_info=context.error)

dispatcher.add_error_handler(bot_error)

# ─── Flask & Webhook Endpoint ───────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK"

if __name__ == "__main__":
    # Register webhook with Telegram
    bot.set_webhook(f"{SERVICE_URL}/webhook")
    # Run Flask (disable auto-reloader)
    app.run(host="0.0.0.0", port=10000, use_reloader=False)

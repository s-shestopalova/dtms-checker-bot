import os
import time
from threading import Thread
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram.ext import Updater, CommandHandler

# ─── Configuration ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
NAME      = os.getenv("NAME", "Max")
SURNAME   = os.getenv("SURNAME", "Mustermann")
EMAIL     = os.getenv("EMAIL", "test@example.com")
PHONE     = os.getenv("PHONE", "0123456789")
URL       = "https://dtms.wiesbaden.de/DTMSTerminWeb/"

# ─── Scraper ───────────────────────────────────────────────────────────────────
def get_appointment_info():
    try:
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=opts)

        driver.get(URL)

        # 1) Klick Fahrerlaubnisbehörde
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Fahrerlaubnisbehörde')]"))
        ).click()

        # 2) Formular ausfüllen
        WebDriverWait(driver, 10).until(lambda d: d.find_element(By.ID, "field-vorname")).send_keys(NAME)
        driver.find_element(By.ID, "field-nachname").send_keys(SURNAME)
        driver.find_element(By.ID, "field-email")   .send_keys(EMAIL)
        driver.find_element(By.ID, "field-telefon") .send_keys(PHONE)
        driver.find_element(By.ID, "datenschutz")   .click()
        driver.find_element(By.XPATH, "//button[contains(text(),'Weiter')]").click()

        # 3) “Umschreibung ausländischer Führerschein” wählen
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

        # 4) Suche starten und Top 3 Termine auslesen
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
        return f"Fehler: {e}"

# ─── Telegram Handler ──────────────────────────────────────────────────────────
def cmd_check(update, context):
    update.message.reply_text(get_appointment_info())

def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("check", cmd_check))
    updater.start_polling()
    # keep thread alive (no idle() to avoid signal calls)
    while True:
        time.sleep(60)

# ─── Flask “Keep-Alive” ─────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running."

# ─── Entrypoint ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)

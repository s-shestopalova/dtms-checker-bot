import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load from env
BOT_TOKEN = os.getenv("BOT_TOKEN")
NAME = os.getenv("NAME", "Max Mustermann")
EMAIL = os.getenv("EMAIL", "test@example.com")
PHONE = os.getenv("PHONE", "0123456789")

URL = "https://dtms.wiesbaden.de/DTMSTerminWeb/"

logging.basicConfig(level=logging.INFO)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_appointment_info()
    await update.message.reply_text(result)

def get_appointment_info():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

        driver.get(URL)

        # Step 1: Click Fahrerlaubnisbehörde
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Fahrerlaubnisbehörde')]"))).click()

        # Step 2: Enter personal info
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "field-vorname"))).send_keys(NAME)
        driver.find_element(By.ID, "field-nachname").send_keys("Test")
        driver.find_element(By.ID, "field-email").send_keys(EMAIL)
        driver.find_element(By.ID, "field-telefon").send_keys(PHONE)
        driver.find_element(By.ID, "datenschutz").click()
        driver.find_element(By.XPATH, "//button[contains(text(),'Weiter')]").click()

        # Step 3: Select "Umschreibung ausländischer Führerschein"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h4[contains(text(),'Umschreibung')]")))
        service = driver.find_element(By.XPATH, "//h4[contains(text(),'Umschreibung')]/ancestor::div[contains(@class, 'leistung')]/descendant::input[@type='number']")
        service.clear()
        service.send_keys("1")
        driver.find_element(By.XPATH, "//button[contains(text(),'Weiter')]").click()

        # Step 4: Search calendar
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Suchen')]"))).click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "appointment")))

        # Step 5: Extract top 3 appointments
        slots = driver.find_elements(By.CLASS_NAME, "appointment")[:3]
        result = "\n".join(slot.text.strip() for slot in slots) or "Keine Termine gefunden."

        driver.quit()
        return result
    except Exception as e:
        return f"Fehler: {e}"

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("check", check))
    app.run_polling()

if __name__ == "__main__":
    main()

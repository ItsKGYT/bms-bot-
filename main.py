import requests
import time

URL = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

BOT_TOKEN = "8640561400:AAFDvFX70zsngNUEL7KOUDZod07pwgKwz68"
CHAT_ID = "410880894"

def send_telegram():
    message = "✅ TEST: Telegram bot is working!\nRailway monitoring is active."

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

print("Testing Telegram notification...")

send_telegram()

print("Test message sent. Bot will now exit.")

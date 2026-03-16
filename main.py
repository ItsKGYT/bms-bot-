import requests
import time

URL = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

BOT_TOKEN = "8640561400:AAFDvFX70zsngNUEL7KOUDZod07pwgKwz68"
CHAT_ID = "410880894"

def notify():
    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": CHAT_ID,
            "text": "🎟 Tickets for March 21 are LIVE!\nhttps://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"
        },
    )

while True:
    r = requests.get(URL)

    if "21" in r.text:
        notify()
        break

    time.sleep(3)

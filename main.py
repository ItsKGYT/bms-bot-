import requests
import time

BOT_TOKEN = "8640561400:AAFdvFX70zsngNUEL7KOUDZ0d07pwgKwx68"
CHAT_ID = "410880894"

URL = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

def send_telegram():
    message = "🎟 Tickets for March 21 are LIVE!\n" + URL

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

while True:
    print("Checking BookMyShow API...")

    try:
        r = requests.get(URL)
        html = r.text

        if "20 Mar" in html:
            print("21 detected!")
            send_telegram()
            break
        else:
            print("21 not available")

    except Exception as e:
        print("Error:", e)

    time.sleep(60)

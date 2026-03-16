import requests
import time

URL = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram():
    message = "🎟 Tickets for March 21 are LIVE!\nhttps://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

while True:
    print("Checking page...")

    try:
        r = requests.get(URL)

        if "21" in r.text:
            print("21 detected!")
            send_telegram()
            break

        else:
            print("21 not available")

    except Exception as e:
        print("Error:", e)

    time.sleep(3)

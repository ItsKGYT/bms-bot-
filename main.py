import time
import requests
from playwright.sync_api import sync_playwright

URL = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/ALUC"

BOT_TOKEN = "8640561400:AAFdvFX70zsngNUEL7KOUDZ0d07pwgKwx68"
CHAT_ID = "410880894"

def send_telegram():
    message = "🎟 Tickets for March 21 are LIVE!\n" + URL

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={"chat_id": CHAT_ID, "text": message},
    )

while True:
    print("Opening browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(URL)
        page.wait_for_timeout(5000)

        html = page.content()

        if "20 Mar" in html:
            print("21 detected!")
            send_telegram()
            browser.close()
            break
        else:
            print("21 not available")

        browser.close()

    time.sleep(60)

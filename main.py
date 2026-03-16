import time
import datetime
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────
#  ✏️  FILL THESE IN BEFORE RUNNING
# ──────────────────────────────────────────────────────────
BOT_TOKEN      = "8640561400:AAFdvFX70zsngNUEL7KOUDZ0d07pwgKwx68"        # From @BotFather
CHAT_ID        = "410880894"          # Your Telegram chat/user ID
# ──────────────────────────────────────────────────────────

TARGET_DATE    = "20260320"                   # March 21 2026
BASE_URL       = "https://in.bookmyshow.com/cinemas/hyderabad/allu-cinemas-kokapet/buytickets/ALUC/{date}"
CHECK_INTERVAL = 5                            # Seconds between checks

URL = BASE_URL.format(date=TARGET_DATE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://in.bookmyshow.com/",
}

# Signs that tickets ARE live
LIVE_SIGNALS = [
    "book now", "buy tickets", "book tickets",
    "__movie-name", "event-title", "__book-now",
    "buyticketssection", "show-date-time",
    "cinemas-list", "showtime",
]

# Signs that tickets are NOT yet available
NOT_LIVE_SIGNALS = [
    "no shows available", "no movies", "coming soon",
    "tickets not available", "currently unavailable",
    "no shows", "shows not available",
]


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API."""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.status_code == 200:
            log("✅ Telegram message sent!")
            return True
        else:
            log(f"❌ Telegram error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False


def check_tickets() -> str:
    """
    Returns:
        "LIVE"      — tickets are bookable
        "NOT_LIVE"  — page loaded but no tickets yet
        "ERROR"     — couldn't fetch the page
    """
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        log(f"HTTP {resp.status_code} — {len(resp.text)} bytes received")

        if resp.status_code != 200:
            return "ERROR"

        html_lower = resp.text.lower()
        soup = BeautifulSoup(resp.text, "html.parser")
        visible_text = soup.get_text(separator=" ").lower()

        # Check for NOT-live signals first
        for signal in NOT_LIVE_SIGNALS:
            if signal in visible_text:
                log(f'  ↳ Not-live signal found: "{signal}"')
                return "NOT_LIVE"

        # Check for live signals
        for signal in LIVE_SIGNALS:
            if signal in html_lower:
                log(f'  ↳ Live signal found: "{signal}"')
                return "LIVE"

        # Heuristic: if the page has meaningful content beyond the nav/footer
        # BMS usually returns a near-empty shell when shows aren't loaded yet
        word_count = len(visible_text.split())
        log(f"  ↳ Visible word count: {word_count}")
        if word_count > 300:
            return "LIVE"

        return "NOT_LIVE"

    except requests.exceptions.RequestException as e:
        log(f"  ↳ Network error: {e}")
        return "ERROR"


def validate_config():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌  Please set BOT_TOKEN in the script before running.")
        print("    Create a bot via @BotFather on Telegram.")
        exit(1)
    if CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("❌  Please set CHAT_ID in the script before running.")
        print("    Visit: https://api.telegram.org/bot<TOKEN>/getUpdates after messaging your bot.")
        exit(1)


def main():
    validate_config()

    log("=" * 60)
    log("🎬  BookMyShow Ticket Monitor Started")
    log(f"    Cinema : Allu Cinemas Kokapet, Hyderabad")
    log(f"    Date   : 21 March 2026")
    log(f"    URL    : {URL}")
    log(f"    Poll   : every {CHECK_INTERVAL}s  ⚡")
    log("=" * 60)

    # Send a startup confirmation to Telegram
    send_telegram(
        "🤖 <b>BMS Monitor Started</b>\n\n"
        "🎬 <b>Cinema:</b> Allu Cinemas Kokapet, Hyderabad\n"
        "📅 <b>Date:</b> 21 March 2026\n"
        f"🔗 <a href='{URL}'>Monitor Link</a>\n\n"
        f"⏱ Checking every {CHECK_INTERVAL} seconds...\n"
        "I'll notify you the moment tickets go live! 🎟️"
    )

    error_count = 0
    check_count = 0

    while True:
        check_count += 1
        log(f"Check #{check_count} — polling BMS...")

        status = check_tickets()

        if status == "LIVE":
            log("🎟️  TICKETS ARE LIVE!")
            alert_msg = (
                "🚨🎟️ <b>TICKETS ARE LIVE!</b> 🎟️🚨\n\n"
                "🎬 <b>Allu Cinemas Kokapet, Hyderabad</b>\n"
                "📅 <b>21 March 2026</b>\n\n"
                f"👉 <a href='{URL}'>BOOK NOW →</a>\n\n"
                "⚡ Hurry before seats fill up!"
            )
            # Send alert 3 times to make sure you don't miss it
            for i in range(3):
                send_telegram(alert_msg)
                if i < 2:
                    time.sleep(5)
            log("✅ Alerts sent. Monitoring complete.")
            break

        elif status == "NOT_LIVE":
            log(f"  ↳ Tickets not live yet. Next check in {CHECK_INTERVAL}s...")
            error_count = 0  # reset error streak

        elif status == "ERROR":
            error_count += 1
            log(f"  ↳ Error #{error_count} fetching page.")
            if error_count == 5:
                send_telegram(
                    "⚠️ <b>BMS Monitor Warning</b>\n\n"
                    "Failed to reach BookMyShow 5 times in a row.\n"
                    "The monitor is still running — this might be a temporary issue.\n\n"
                    f"🔗 <a href='{URL}'>Check manually</a>"
                )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

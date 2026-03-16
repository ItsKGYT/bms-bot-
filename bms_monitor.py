import os
import time
import datetime
import random
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────
#  CONFIG — reads from Railway env vars if set, else uses
#  the hardcoded values below
# ──────────────────────────────────────────────────────────
BOT_TOKEN       = os.environ.get("BOT_TOKEN",       "8640561400:AAGoFl81jL6hxhEOVtrfAXpKu3mexjVT16g")
CHAT_ID         = os.environ.get("CHAT_ID",         "410880894")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "YOUR_SCRAPERAPI_KEY_HERE")
# ──────────────────────────────────────────────────────────

TARGET_DATE    = "20260321"
CINEMA_CODE    = "ALUC"
CHECK_INTERVAL = 5  # seconds

PAGE_URL = (
    f"https://in.bookmyshow.com/cinemas/hyderabad/"
    f"allu-cinemas-kokapet/buytickets/{CINEMA_CODE}/{TARGET_DATE}"
)

# BMS internal showtimes API
API_URL = (
    f"https://in.bookmyshow.com/api/movies-data/showtimes-by-event"
    f"?appCode=MOBAND2&appVersion=14.3.4&language=en"
    f"&venueCode={CINEMA_CODE}&date={TARGET_DATE}&skip=0&limit=100&filterKey=movies"
)

# ScraperAPI wraps any URL through residential IPs
def scraper_url(target: str) -> str:
    return f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={target}&country_code=in"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

LIVE_SIGNALS = [
    "book now", "buy tickets", "book tickets",
    "__movie-name", "__book-now", "buyticketssection",
    "show-date-time", "showtime", "cinemas-list",
    "data-booking-type", "venue-show-time",
]

NOT_LIVE_SIGNALS = [
    "no shows available", "no movies", "coming soon",
    "tickets not available", "currently unavailable",
    "no shows", "shows not available", "be the first to know",
]


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Telegram ────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            log("✅ Telegram message sent!")
            return True
        else:
            err = data.get("description", resp.text)
            log(f"❌ Telegram error {resp.status_code}: {err}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False


# ── Direct session (works if Railway IP not blocked) ─────────

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    })
    try:
        session.get("https://in.bookmyshow.com/", timeout=10)
        log("  ↳ Session cookies primed ✓")
    except Exception as e:
        log(f"  ↳ Session prime warning: {e}")
    return session


# ── Check methods ────────────────────────────────────────────

def parse_html(html: str) -> str:
    """Parse BMS HTML and return LIVE / NOT_LIVE.
    
    IMPORTANT: BMS redirects the 21 Mar URL to today's shows until
    21 Mar tickets actually go on sale. So we MUST confirm the page
    is genuinely showing March 21 content before alerting.
    """
    html_lower = html.lower()
    soup = BeautifulSoup(html, "html.parser")
    visible_text = soup.get_text(separator=" ").lower()

    # ── Step 1: Confirm the page is actually for March 21 ──
    # BMS will redirect to today's date until 21 Mar goes live.
    # We check for "21" near "march" or "mar" in the page text,
    # OR the target date string in the HTML itself.
    date_confirmed = False
    date_markers = [
        "21 mar", "mar 21", "21st mar", "march 21",
        "20260321", "2026-03-21", "21/03/2026",
        ">21<", "date=20260321",
    ]
    for marker in date_markers:
        if marker in html_lower:
            log(f'  ↳ Date confirmed: found "{marker}" in page ✅')
            date_confirmed = True
            break

    if not date_confirmed:
        log("  ↳ March 21 date NOT found in page — BMS is showing a different date, ignoring.")
        return "NOT_LIVE"

    # ── Step 2: Check if shows are actually available ──
    for signal in NOT_LIVE_SIGNALS:
        if signal in visible_text:
            log(f'  ↳ Not-live signal: "{signal}"')
            return "NOT_LIVE"

    for signal in LIVE_SIGNALS:
        if signal in html_lower:
            log(f'  ↳ Live signal: "{signal}"')
            return "LIVE"

    word_count = len(visible_text.split())
    log(f"  ↳ Word count: {word_count}")
    return "LIVE" if word_count > 400 else "NOT_LIVE"


def check_direct(session: requests.Session) -> str:
    """Try hitting BMS directly (fast, may 403 on Railway)."""
    try:
        session.headers["Referer"] = "https://in.bookmyshow.com/"
        resp = session.get(PAGE_URL, timeout=15)
        log(f"  [DIRECT] HTTP {resp.status_code} — {len(resp.text)} bytes")

        if resp.status_code == 403:
            return "BLOCKED"
        if resp.status_code != 200:
            return "ERROR"
        return parse_html(resp.text)

    except Exception as e:
        log(f"  [DIRECT] Exception: {e}")
        return "ERROR"


def check_via_scraperapi() -> str:
    """Route through ScraperAPI residential IPs — bypasses Railway IP block."""
    if SCRAPER_API_KEY == "YOUR_SCRAPERAPI_KEY_HERE":
        log("  [SCRAPER] Skipped — no ScraperAPI key set")
        return "ERROR"
    try:
        url = scraper_url(PAGE_URL)
        resp = requests.get(url, timeout=60)  # ScraperAPI can be slow
        log(f"  [SCRAPER] HTTP {resp.status_code} — {len(resp.text)} bytes")

        if resp.status_code == 200:
            return parse_html(resp.text)
        else:
            log(f"  [SCRAPER] Failed: {resp.status_code}")
            return "ERROR"

    except Exception as e:
        log(f"  [SCRAPER] Exception: {e}")
        return "ERROR"


def check_via_api(session: requests.Session) -> str:
    """Hit BMS internal JSON API — sometimes less blocked than HTML."""
    try:
        api_headers = {
            "x-bms-id": "IN-HYD",
            "x-region-code": "HYD",
            "x-region-slug": "hyderabad",
            "x-subregion-code": "",
            "Accept": "application/json, text/plain, */*",
            "Referer": PAGE_URL,
            "Origin": "https://in.bookmyshow.com",
        }
        resp = session.get(API_URL, headers=api_headers, timeout=15)
        log(f"  [API] HTTP {resp.status_code} — {len(resp.text)} bytes")

        if resp.status_code == 200:
            data = resp.json()
            # Verify the API actually returned data for Mar 21 specifically
            resp_text = resp.text
            if "20260321" not in resp_text and "2026-03-21" not in resp_text:
                log("  ↳ API response doesn't mention 20260321 — not yet live for Mar 21")
                return "NOT_LIVE"
            movies = data.get("BookMyShow", {}).get("arrEvents", [])
            if movies:
                log(f"  ↳ API found {len(movies)} movie(s) for Mar 21! 🎬")
                return "LIVE"
            return "NOT_LIVE"
        elif resp.status_code == 403:
            return "BLOCKED"
        return "ERROR"

    except Exception as e:
        log(f"  [API] Exception: {e}")
        return "ERROR"


def check_tickets(session: requests.Session) -> str:
    """
    Try in order:
      1. Direct request (fast)
      2. BMS internal API (if direct is blocked)
      3. ScraperAPI (residential IP proxy — always works)
    """
    result = check_direct(session)

    if result == "BLOCKED":
        log("  ↳ Direct blocked, trying internal API...")
        result = check_via_api(session)

    if result in ("BLOCKED", "ERROR"):
        log("  ↳ Falling back to ScraperAPI (residential IP)...")
        result = check_via_scraperapi()

    return result


# ── Config validation ────────────────────────────────────────

def validate_config():
    errors = []
    if not BOT_TOKEN or "YOUR" in BOT_TOKEN:
        errors.append("❌  BOT_TOKEN not set!")
    elif ":" not in BOT_TOKEN:
        errors.append("❌  BOT_TOKEN format wrong — must contain ':'")
    if not CHAT_ID or "YOUR" in CHAT_ID:
        errors.append("❌  CHAT_ID not set!")
    if errors:
        for e in errors:
            print(e)
        exit(1)

    if SCRAPER_API_KEY == "YOUR_SCRAPERAPI_KEY_HERE":
        log("⚠️  No ScraperAPI key — will rely on direct requests only.")
        log("   If Railway IPs get blocked, get a free key at https://www.scraperapi.com")


# ── Main ─────────────────────────────────────────────────────

def main():
    validate_config()

    SESSION = make_session()
    session_refresh_counter = 0

    log("=" * 60)
    log("🎬  BookMyShow Monitor v3 (Railway) Started")
    log(f"    Cinema : Allu Cinemas Kokapet, Hyderabad")
    log(f"    Date   : 21 March 2026")
    log(f"    Poll   : every {CHECK_INTERVAL}s ⚡")
    log(f"    ScraperAPI : {'✅ configured' if SCRAPER_API_KEY != 'YOUR_SCRAPERAPI_KEY_HERE' else '⚠️  not set (optional)'}")
    log("=" * 60)

    send_telegram(
        "🤖 <b>BMS Monitor v3 Started</b> (Railway)\n\n"
        "🎬 <b>Cinema:</b> Allu Cinemas Kokapet, Hyderabad\n"
        "📅 <b>Date:</b> 21 March 2026\n"
        f"🔗 <a href='{PAGE_URL}'>Monitor Link</a>\n\n"
        f"⚡ Checking every {CHECK_INTERVAL} seconds\n"
        "I'll alert you the moment tickets go live! 🎟️"
    )

    error_count = 0
    check_count = 0

    while True:
        check_count += 1
        session_refresh_counter += 1
        log(f"Check #{check_count} — polling BMS...")

        if session_refresh_counter >= 60:
            log("  ↳ Refreshing session...")
            SESSION = make_session()
            session_refresh_counter = 0

        status = check_tickets(SESSION)

        if status == "LIVE":
            log("🎟️  TICKETS ARE LIVE!")
            alert_msg = (
                "🚨🎟️ <b>TICKETS ARE LIVE!</b> 🎟️🚨\n\n"
                "🎬 <b>Allu Cinemas Kokapet, Hyderabad</b>\n"
                "📅 <b>21 March 2026</b>\n\n"
                f"👉 <a href='{PAGE_URL}'>BOOK NOW →</a>\n\n"
                "⚡ Hurry before seats fill up!"
            )
            for i in range(3):
                send_telegram(alert_msg)
                if i < 2:
                    time.sleep(3)
            log("✅ Alerts sent. Re-alerting every 60s — worker staying alive...")
            # Keep Railway worker alive + keep pinging you every minute
            while True:
                time.sleep(60)
                send_telegram(
                    f"🔔 <b>REMINDER: Tickets still live!</b>\n\n"
                    f"👉 <a href='{PAGE_URL}'>BOOK NOW →</a>"
                )

        elif status == "NOT_LIVE":
            log(f"  ↳ Not live yet. Next check in {CHECK_INTERVAL}s...")
            error_count = 0

        elif status in ("ERROR", "BLOCKED"):
            error_count += 1
            log(f"  ↳ All methods failed (#{error_count}). Refreshing session...")
            SESSION = make_session()
            session_refresh_counter = 0
            if error_count == 10:
                send_telegram(
                    "⚠️ <b>BMS Monitor Warning</b>\n\n"
                    "10 consecutive failures on Railway.\n"
                    "💡 Fix: Add a free ScraperAPI key to bypass IP blocks.\n"
                    "→ https://www.scraperapi.com\n\n"
                    f"🔗 <a href='{PAGE_URL}'>Check manually</a>"
                )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

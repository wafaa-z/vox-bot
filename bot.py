import os
import re
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
CHAT_ID = (os.getenv("CHAT_ID") or "").strip()

CINEMA_URL = "https://egy.voxcinemas.com/showtimes?c=city-centre-almaza"
MOVIE_KEYWORD = "doomsday"
TARGET_FORMAT = "4dx"

TARGET_DATES = [
    ("20261216", "16 Dec"),
    ("20261217", "17 Dec"),
    ("20261218", "18 Dec"),
    ("20261219", "19 Dec"),
    ("20261220", "20 Dec"),
]


def send_telegram_alert(message):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message}
  res = requests.post(url, data=payload, timeout=15)
  print("📩 رد تيليجرام:", res.status_code, res.text)


def check_almaza_4dx():
  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            "--disable-http2",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = context.new_page()

    print("🌐 جاري فتح صفحة عروض سيتي سنتر ألماظة...")
    page.goto(CINEMA_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    found_matches = []

    for date_code, date_label in TARGET_DATES:
      day_tab = page.locator(
          f'a[href*="d={date_code}"], a:has-text("{date_label}"),'
          f' button:has-text("{date_label}")'
      ).first

      if day_tab.count() == 0:
        print(f"📅 {date_label}: لسا ما نزل في جدول ألماظة.")
        continue

      day_tab.click()
      page.wait_for_timeout(3000)

      headings = page.locator("h2, h3").filter(
          has_text=re.compile(MOVIE_KEYWORD, re.I)
      )

      for i in range(headings.count()):
        heading = headings.nth(i)
        version_name = heading.inner_text().strip()
        card = heading

        for _ in range(6):
          card = card.locator("..")
          if card.count() == 0:
            break

          movie_links = card.locator('a[href*="/movies/"]').all()
          unique_movies = {
              link.get_attribute("href").split("?")[0].strip("/")
              for link in movie_links
              if link.get_attribute("href")
          }
          if len(unique_movies) > 1:
            break

          text = card.inner_text().lower()
          has_showtimes_block = (
              ("city centre almaza" in text)
              or ("am" in text)
              or ("pm" in text)
              or (card.locator('a[href*="/booking"]').count() > 0)
          )

          if has_showtimes_block:
            if TARGET_FORMAT.lower() in text:
              print(f"🚨 {date_label} [{version_name}]: فتح حجز 4DX!")
              found_matches.append(f"{date_label} ({version_name})")
            else:
              print(f"⏳ {date_label} [{version_name}]: 4DX لسا ما نزل.")
            break

    if found_matches:
      details = "\n• ".join(found_matches)
      send_telegram_alert(
          "يلاه يا حسان يلاه يا نجوى الفلم نزل يلاه نحجز هيا بسرعه واهعاهاعاها"
          f" 😂😂😂\n\nالعروض المتاحة (4DX):\n• {details}\n\nرابط الحجز"
          f" المباشر:\n{CINEMA_URL}"
      )
      print("\n✅ انتهت محاولة الإرسال!")
    else:
      print("\n❌ ما نزل 4DX في أي نسخة من 16 إلى 20 ديسمبر لحد الحين.")

    browser.close()


if __name__ == "__main__":
  check_almaza_4dx()

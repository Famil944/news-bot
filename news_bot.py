import os
import asyncio
import feedparser
import aiohttp
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import pytz

# Загружаем переменные из .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("API_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHANNEL")

# Московское время
moscow_tz = pytz.timezone("Europe/Moscow")

# RSS-источник
RSS_URL = "https://lenta.ru/rss"

# Запоминаем, что уже отправляли
sent_titles = set()

# Ключевые слова для фильтрации
IMPORTANT_KEYWORDS = ["погиб", "взрыв", "катастроф", "теракт", "убит", "произошло", "срочно", "чрезвычайн", "авария", "загорел", "стрельб", "обстрел"]

def is_important(title: str) -> bool:
    """Проверка, содержит ли заголовок важные ключевые слова."""
    lower_title = title.lower()
    return any(keyword in lower_title for keyword in IMPORTANT_KEYWORDS)

async def send_telegram_message(session: aiohttp.ClientSession, text: str):
    """Отправка сообщения в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    async with session.post(url, data=payload) as response:
        if response.status != 200:
            error = await response.text()
            print(f"❌ Ошибка отправки: {error}")

async def check_news(scheduled=False):
    """Проверка RSS и отправка важных новостей."""
    print(f"\n[{datetime.now(moscow_tz):%Y-%m-%d %H:%M:%S}] 🔍 Проверка новостей (scheduled={scheduled}) — UTC: {datetime.utcnow()}")

    feed = feedparser.parse(RSS_URL)
    async with aiohttp.ClientSession() as session:
        for entry in feed.entries:
            title = entry.title
            link = entry.link

            if title not in sent_titles and is_important(title):
                print(f"📢 Отправляем важную новость: {title}")
                sent_titles.add(title)
                await send_telegram_message(session, f"<b>{title}</b>\n{link}")

    if not any(is_important(entry.title) and entry.title not in sent_titles for entry in feed.entries):
        print("🚫 Нет важных новостей.")

def setup_scheduler():
    """Настройка расписания."""
    scheduler = AsyncIOScheduler(timezone=moscow_tz)

    scheduler.add_job(check_news, 'cron', hour=8, minute=0, kwargs={'scheduled': True})   # Утро
    scheduler.add_job(check_news, 'cron', hour=13, minute=0, kwargs={'scheduled': True})  # День
    scheduler.add_job(check_news, 'cron', hour=18, minute=0, kwargs={'scheduled': True})  # Вечер
    scheduler.add_job(check_news, 'cron', hour=23, minute=0, kwargs={'scheduled': True})  # Ночь

    scheduler.start()

async def main():
    print("🤖 Бот запущен и слушает RSS...")
    await check_news()
    setup_scheduler()

    while True:
        await asyncio.sleep(60)  # Чтобы процесс не завершался

if __name__ == "__main__":
    asyncio.run(main())
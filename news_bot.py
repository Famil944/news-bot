import os
import asyncio
import feedparser
from aiogram import Bot
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz

# Загрузка токена и канала
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
CHANNEL = os.getenv("CHANNEL")

bot = Bot(token=API_TOKEN)

# Список RSS-лент
RSS_FEEDS = [
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",
]

# Файл с уже отправленными ссылками
SENT_FILE = "sent.txt"
if not os.path.exists(SENT_FILE):
    open(SENT_FILE, "w").close()

with open(SENT_FILE, "r", encoding="utf-8") as f:
    sent_links = set(f.read().splitlines())

# Фильтр для важных новостей
IMPORTANT_KEYWORDS = ["срочно", "важно", "экстренно", "немедленно", "молния"]

# Проверка на важность
def is_important(title):
    lower_title = title.lower()
    return any(keyword in lower_title for keyword in IMPORTANT_KEYWORDS)

# Получение новых новостей
async def get_new_posts():
    new_posts = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            link = entry.link
            title = entry.title
            if link not in sent_links:
                message = f"{title}\n{link}"
                new_posts.append((link, title, message))
                sent_links.add(link)
    return new_posts

# Отправка новостей
async def send_news(scheduled=False):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Проверка новостей (scheduled={scheduled})")
    posts = await get_new_posts()
    if not posts:
        print("Нет новых новостей.")
        return

    for link, title, message in posts:
        try:
            if scheduled or not is_important(title):
                # Отправка по расписанию
                await bot.send_message(CHANNEL, message)
                print(f"📤 Отправлено: {title}")
                await asyncio.sleep(2)
            else:
                # Немедленная отправка важных
                print(f"⚡ Важная новость — отправляем сразу: {title}")
                await bot.send_message(CHANNEL, message)
                await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ Ошибка при отправке: {e}")

    # Сохраняем ссылки
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sent_links))

# Настройка расписания
def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))

    # Каждые 10 минут — только важные (внутри send_news решается)
    scheduler.add_job(send_news, "interval", minutes=10, kwargs={"scheduled": False})

    # Расписание для обычных новостей
    scheduler.add_job(send_news, CronTrigger(hour=8, minute=0), kwargs={"scheduled": True})   # Утро
    scheduler.add_job(send_news, CronTrigger(hour=13, minute=0), kwargs={"scheduled": True})  # День
    scheduler.add_job(send_news, CronTrigger(hour=18, minute=0), kwargs={"scheduled": True})  # Вечер
    scheduler.add_job(send_news, CronTrigger(hour=23, minute=0), kwargs={"scheduled": True})  # Ночь

    scheduler.start()
    print("📆 Планировщик запущен.")

# Главная функция
async def main():
    print("🤖 Бот запущен и слушает RSS...")

    # Сразу проверим важные при запуске
    await send_news(scheduled=False)

    setup_scheduler()

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
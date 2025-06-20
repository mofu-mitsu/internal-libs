import random
import atproto
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio
import yaml
import os

# yml読み込み
with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

seasonal_notes = config["seasonal_notes"]
handle = os.getenv("HANDLE", config.get("HANDLE", ""))
password = os.getenv("APP_PASSWORD", config.get("APP_PASSWORD", ""))

async def post_seasonal_note():
    try:
        client = atproto.Client()
        client.login(handle, password)
        current_month = datetime.now().month
        note = random.choice(seasonal_notes[str(current_month)])
        await client.post(text=note)
        print(f"Posted: {note}")
    except Exception as e:
        print(f"Error: {e}")

# スケジューラ設定
scheduler = AsyncIOScheduler()
scheduler.add_job(
    post_seasonal_note,
    "cron",
    day=config["schedule"]["day"],
    hour=config["schedule"]["hour"],
    minute=config["schedule"]["minute"]
)
scheduler.start()

# イベントループ
async def main():
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())

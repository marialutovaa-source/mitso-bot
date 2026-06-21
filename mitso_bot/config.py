import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

SCHEDULE_URL = "https://apps.mitso.by/frontend/web/schedule/group-schedule"

PHOTOS_DIR = "photos"

SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "").split(",") if x.strip()]

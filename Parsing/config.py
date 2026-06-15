import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("DND_BASE_URL", "https://dnd.su").rstrip("/")
EQUIPMENT_BASE_URL = os.getenv("DND_EQUIPMENT_BASE_URL", "https://next.dnd.su").rstrip("/")
SOURCE_CODE = os.getenv("DND_SOURCE_CODE", "PH14")
SOURCE_NAME = os.getenv("DND_SOURCE_NAME", "Player's Handbook 2014")
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.7"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DnD-Randomizer-Parser/1.0"
}

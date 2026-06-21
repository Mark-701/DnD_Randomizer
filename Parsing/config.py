import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('DND_BASE_URL', 'https://dnd.su').rstrip('/')
SITEMAP_URL = os.getenv('DND_SITEMAP_URL', f'{BASE_URL}/sitemap.xml')
SOURCE_CODE = os.getenv('DND_SOURCE_CODE', 'PH14')
SOURCE_NAME = os.getenv('DND_SOURCE_NAME', "Player's Handbook 2014")
REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', '0.35'))

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '7010')
DB_NAME = os.getenv('DB_NAME', 'DnD')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '701')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DnD-Randomizer-Parser/2.0'
}

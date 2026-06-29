import os

from dotenv import load_dotenv


load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

DOWNLOAD_FOLDER = "downloads"
LINKS_FILE = "links.txt"
FAILED_LOG_FILE = "failed_links.txt"

MAX_CONCURRENT_DOWNLOADS = 2

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

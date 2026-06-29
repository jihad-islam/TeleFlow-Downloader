import os
import re

from telethon import TelegramClient
from telethon.tl.types import Channel, User

from src.config import DOWNLOAD_FOLDER
from src.utils import log_failed_link, ProgressCallback


async def download_link(client: TelegramClient, link: str, semaphore):
    """Download a single Telegram message media item into its chat folder."""
    async with semaphore:
        private = re.search(r"t\.me/c/(\d+)/(\d+)", link)
        public = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)

        try:
            if private:
                entity = int("-100" + private.group(1))
                message_id = int(private.group(2))
            elif public:
                username = public.group(1)
                message_id = int(public.group(2))
                entity = await client.get_entity(username)
            else:
                print(f"\n❌ Invalid Link: {link}")
                log_failed_link(link, "Invalid Link Format")
                return None

            message = await client.get_messages(entity, ids=message_id)

            if not message or not message.media:
                print(f"\n❌ No media found: {link}")
                log_failed_link(link, "No media or message found")
                return None

            chat = await client.get_entity(entity)
            folder_name = "Unknown_Chat"
            if isinstance(chat, Channel):
                folder_name = chat.title
            elif isinstance(chat, User):
                folder_name = chat.username or chat.first_name

            safe_folder_name = "".join(
                x for x in folder_name if x.isalnum() or x in " _-"
            )
            chat_folder = os.path.join(DOWNLOAD_FOLDER, safe_folder_name)
            os.makedirs(chat_folder, exist_ok=True)

            file_name = message.file.name or f"{message.id}{message.file.ext}"
            file_path = os.path.join(chat_folder, file_name)

            if os.path.exists(file_path):
                print(f"\n⏭️ Already downloaded, skipping: {file_name}")
                return file_path

            print(f"\n⬇️ Task Started: {file_name} (from {folder_name})")

            progress = ProgressCallback(file_name, action="Downloading")
            path = await client.download_media(
                message,
                file=file_path,
                progress_callback=progress,
            )

            return path

        except Exception as e:
            print(f"\n❌ Error downloading {link}: {e}")
            log_failed_link(link, str(e))
            return None

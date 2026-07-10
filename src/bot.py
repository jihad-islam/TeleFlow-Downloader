import asyncio
import os
import re

from telethon import events

from src.config import DOWNLOAD_FOLDER, MAX_CONCURRENT_DOWNLOADS
from src.downloader import download_links_with_limit
from src.utils import (
    ProgressCallback,
    TelegramStatusProgressReporter,
    reset_status_progress_reporter,
    set_status_progress_reporter,
)


def is_video_media(message, path):
    """Return True when a downloaded file should be uploaded as Telegram video."""
    message_file = getattr(message, "file", None)
    mime_type = getattr(message_file, "mime_type", "") or ""
    if mime_type.startswith("video/"):
        return True

    video_extensions = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"}
    return os.path.splitext(path)[1].lower() in video_extensions


async def download_video_thumbnail(client, message, path):
    """Download the source video thumbnail so re-upload keeps a visual preview."""
    thumb_path = f"{path}.thumb.jpg"

    try:
        downloaded_thumb = await client.download_media(
            message,
            thumb=-1,
            file=thumb_path,
        )
    except Exception:
        return None

    if downloaded_thumb and os.path.exists(downloaded_thumb):
        return downloaded_thumb
    return None


def get_video_upload_options(message, path, thumb_path):
    """Build Telethon send_file options that keep videos playable in chat."""
    if not is_video_media(message, path):
        return {}

    document = getattr(message, "document", None)
    attributes = getattr(document, "attributes", None)
    options = {
        "force_document": False,
        "supports_streaming": True,
    }

    if attributes:
        options["attributes"] = attributes

    if thumb_path:
        options["thumb"] = thumb_path

    return options


def normalize_telegram_link(link_suffix):
    """Return a full Telegram URL from a matched message link."""
    return (
        f"https://{link_suffix}"
        if not link_suffix.startswith("http")
        else link_suffix
    )


def chunk_items(items, size):
    """Yield fixed-size chunks from a list."""
    for index in range(0, len(items), size):
        yield items[index : index + size]


def remove_empty_download_folders():
    """Remove empty subfolders left behind after bot uploads are cleaned up."""
    for root, dirs, _ in os.walk(DOWNLOAD_FOLDER, topdown=False):
        for folder_name in dirs:
            folder_path = os.path.join(root, folder_name)
            try:
                os.rmdir(folder_path)
            except OSError:
                pass


async def upload_file_with_limit(client, path, semaphore):
    """Upload one file to Telegram while respecting the shared transfer limit."""
    async with semaphore:
        file_name = os.path.basename(path)
        return await client.upload_file(
            path,
            progress_callback=ProgressCallback(file_name, action="Uploading"),
        )


async def process_bot_downloads(client, event, links, semaphore):
    status_message = await client.send_message("me", "⏳ Downloading...")

    download_reporter = TelegramStatusProgressReporter(
        status_message,
        action="Downloading",
    )
    token = set_status_progress_reporter(download_reporter)
    try:
        downloaded_items = await download_links_with_limit(
            client,
            links,
            semaphore,
            MAX_CONCURRENT_DOWNLOADS,
            include_message=True,
        )
    finally:
        reset_status_progress_reporter(token)
        download_reporter.stop()
        await download_reporter.wait()

    downloaded_items = [item for item in downloaded_items if item]
    if not downloaded_items:
        await status_message.edit("❌ Download failed")
        await asyncio.sleep(5)
        await status_message.delete()
        print(f"❌ Process failed for {len(links)} link(s).")
        return

    paths = [item.path for item in downloaded_items]
    is_group_upload = len(paths) > 1
    file_name = os.path.basename(paths[0])

    await status_message.edit("✅ Download complete")
    await asyncio.sleep(1)
    await status_message.edit("⏫ Uploading...")

    thumb_path = None
    upload_target = paths
    upload_options = {
        "force_document": False,
        "supports_streaming": True,
    }

    if not is_group_upload:
        source_message = downloaded_items[0].message
        path = paths[0]
        if is_video_media(source_message, path):
            thumb_path = await download_video_thumbnail(client, source_message, path)
        upload_target = path
        upload_options = get_video_upload_options(source_message, path, thumb_path)

    upload_reporter = TelegramStatusProgressReporter(
        status_message,
        action="Uploading",
    )
    token = set_status_progress_reporter(upload_reporter)
    try:
        if is_group_upload:
            upload_tasks = [
                asyncio.create_task(
                    upload_file_with_limit(client, path, semaphore)
                )
                for path in upload_target
            ]
            uploaded_files = await asyncio.gather(*upload_tasks)
            await status_message.edit("⏫ Sending grouped media...")

            for upload_chunk in chunk_items(uploaded_files, 10):
                await client.send_file(
                    "me",
                    upload_chunk,
                    **upload_options,
                )
        else:
            await client.send_file(
                "me",
                upload_target,
                progress_callback=ProgressCallback(file_name, action="Uploading"),
                **upload_options,
            )
    except Exception as e:
        upload_reporter.stop()
        await upload_reporter.wait()
        await status_message.edit("❌ Upload failed")
        await asyncio.sleep(5)
        await status_message.delete()
        print(f"❌ Upload failed for {len(downloaded_items)} file(s): {e}")
        return
    finally:
        reset_status_progress_reporter(token)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

    upload_reporter.stop()
    await upload_reporter.wait()

    await status_message.edit("✅ Upload complete")
    await asyncio.sleep(2)
    await status_message.delete()

    for path in dict.fromkeys(paths):
        if os.path.exists(path):
            os.remove(path)
    remove_empty_download_folders()
    print(f"✅ Auto-deleted from PC: {len(paths)} file(s)")

    await event.delete()
    print("🗑️ Deleted original link from Saved Messages.")


async def run_bot(client):
    """Watch Saved Messages for Telegram links and upload downloads back there."""
    print("\n🤖 Bot Mode Activated (Cloud Storage Mode)!")
    print("📲 Send any Telegram link to your 'Saved Messages'.")
    print("🤫 Silent mode: Progress will only show here in the terminal.")
    print("🛑 Send '/stop' to safely close this script from your phone.")
    print("⏳ Script is running in the background. Press 'Ctrl+C' to exit.\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    @client.on(events.NewMessage(chats="me"))
    async def handler(event):
        text = event.raw_text.strip().lower()

        if text == "/stop":
            print("\n🛑 Stop command received from Telegram. Shutting down...")
            await event.delete()
            await client.disconnect()
            return

        links = re.findall(r"t\.me/\S+", text)
        if not links:
            return

        print(f"\n🔗 Bot received {len(links)} link(s). Processing...")

        full_links = [normalize_telegram_link(link_suffix) for link_suffix in links]
        asyncio.create_task(process_bot_downloads(client, event, full_links, semaphore))

    await client.run_until_disconnected()

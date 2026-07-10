import argparse
import asyncio
import os
import re
import sys
import time

from telethon import TelegramClient, events

from src.config import (
    API_ID,
    API_HASH,
    DOWNLOAD_FOLDER,
    LINKS_FILE,
    MAX_CONCURRENT_DOWNLOADS,
)
from src.downloader import download_link
from src.utils import (
    ProgressCallback,
    TelegramStatusProgressReporter,
    reset_status_progress_reporter,
    set_status_progress_reporter,
)


SEPARATOR = "=" * 50


def get_phone():
    """Read and normalize a Bangladeshi phone number for Telethon login."""
    phone = input("\nEnter your phone number (e.g., 01712345678): ").strip()
    if not phone.startswith("+88"):
        if phone.startswith("0"):
            phone = "+88" + phone
        else:
            phone = "+880" + phone
    return phone


def format_output_directory(path):
    """Return a display-friendly output directory path."""
    return path if path.endswith(os.sep) else f"{path}{os.sep}"


def format_duration(seconds):
    """Format elapsed seconds for the CLI summary."""
    total_seconds = int(round(seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes:02d}m {seconds:02d}s"


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


def print_startup_info(link_count):
    """Print the CLI batch startup information."""
    print()
    print(SEPARATOR)
    print("📥 TeleFlow Downloader - CLI Mode")
    print(SEPARATOR)
    print()
    print(f"Loaded Links      : {link_count}")
    print(f"Concurrent Jobs   : {MAX_CONCURRENT_DOWNLOADS}")
    print(f"Output Directory  : {format_output_directory(DOWNLOAD_FOLDER)}")
    print()
    print(SEPARATOR)
    print("Starting downloads...")
    print("=====================")
    print()


def print_download_summary(successful, failed, elapsed_seconds):
    """Print the CLI batch summary."""
    print()
    print(SEPARATOR)
    print("Download Summary")
    print(SEPARATOR)
    print()
    print(f"✅ Successful : {successful}")
    print(f"❌ Failed     : {failed}")
    print(f"⏱ Total Time : {format_duration(elapsed_seconds)}")
    print()
    print(SEPARATOR)
    print()


def print_exit_message():
    """Print a clean CLI exit message."""
    print()
    print(SEPARATOR)
    print("👋 Thank you for using TeleFlow Downloader!")
    print()
    print("Goodbye and have a great day.")
    print(SEPARATOR)


def ask_download_more():
    """Ask whether another CLI batch should be downloaded."""
    while True:
        answer = input("Would you like to download more files? (y/n): ").strip().lower()

        if answer in {"y", "n"}:
            return answer == "y"

        print("Please enter 'y' for yes or 'n' for no.")


def prompt_for_links():
    """Read one or more Telegram links from stdin."""
    while True:
        print()
        print("Enter Telegram link(s)")
        print("(One link per line. Press Enter on an empty line to start downloading.)")
        print()

        links = []
        blank_lines_before_links = 0
        while True:
            line = input().strip()

            if line == "":
                if links:
                    break
                blank_lines_before_links += 1
                if blank_lines_before_links >= 2:
                    print("No links were entered. Please add at least one Telegram link.")
                    break
                continue

            links.append(line)

        if links:
            return links


def load_links_from_file():
    """Load non-empty links from the configured links file."""
    if not os.path.exists(LINKS_FILE):
        return []

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def clear_links_file():
    """Empty the links file without deleting it."""
    with open(LINKS_FILE, "w", encoding="utf-8"):
        pass


async def run_cli_batch(client, links):
    """Run one CLI download batch and print its summary."""
    print_startup_info(len(links))

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    tasks = []
    start_time = time.monotonic()

    for link in links:
        task = asyncio.create_task(download_link(client, link, semaphore))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    elapsed_seconds = time.monotonic() - start_time
    successful = sum(1 for result in results if result)
    failed = len(results) - successful

    print_download_summary(successful, failed, elapsed_seconds)


async def run_cli(client):
    """Download Telegram links from the links file or interactive input."""
    links = load_links_from_file()
    links_loaded_from_file = bool(links)

    if not links:
        print(f"No links found in {LINKS_FILE}.")
        links = prompt_for_links()

    while True:
        await run_cli_batch(client, links)

        if links_loaded_from_file:
            clear_links_file()
            links_loaded_from_file = False

        if not ask_download_more():
            print_exit_message()
            return

        links = prompt_for_links()


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

    async def process_bot_downloads(client, event, links, semaphore):
        status_message = await client.send_message("me", "⏳ Downloading...")

        download_reporter = TelegramStatusProgressReporter(
            status_message,
            action="Downloading",
        )
        token = set_status_progress_reporter(download_reporter)
        try:
            download_tasks = [
                asyncio.create_task(
                    download_link(
                        client,
                        link,
                        semaphore,
                        include_message=True,
                    )
                )
                for link in links
            ]
            downloaded_items = await asyncio.gather(*download_tasks)
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
                for upload_chunk in chunk_items(upload_target, 10):
                    await client.send_file(
                        "me",
                        upload_chunk,
                        progress_callback=ProgressCallback(
                            file_name,
                            action="Uploading",
                        ),
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
        print(f"✅ Auto-deleted from PC: {len(paths)} file(s)")

        await event.delete()
        print("🗑️ Deleted original link from Saved Messages.")

    await client.run_until_disconnected()


def main():
    """Parse arguments, start the Telegram client, and run the selected mode."""
    parser = argparse.ArgumentParser(description="Telegram Downloader (CLI & Bot Mode)")
    parser.add_argument(
        "--mode",
        choices=["cli", "bot"],
        default="cli",
        help="Run mode: cli or bot",
    )
    args = parser.parse_args()

    print("Initializing Telegram Client...")
    client = TelegramClient("my_account_session", API_ID, API_HASH)

    with client:
        client.start(phone=get_phone)

        if args.mode == "cli":
            client.loop.run_until_complete(run_cli(client))

        elif args.mode == "bot":
            client.loop.run_until_complete(run_bot(client))


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Script stopped manually (Ctrl+C). Goodbye!")
        sys.exit(0)

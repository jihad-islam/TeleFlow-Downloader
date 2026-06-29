import argparse
import asyncio
import os
import re
import sys

from telethon import TelegramClient, events

from src.config import API_ID, API_HASH, LINKS_FILE, MAX_CONCURRENT_DOWNLOADS
from src.downloader import download_link
from src.utils import (
    ProgressCallback,
    TelegramStatusProgressReporter,
    reset_status_progress_reporter,
    set_status_progress_reporter,
)


def get_phone():
    """Read and normalize a Bangladeshi phone number for Telethon login."""
    phone = input("\nEnter your phone number (e.g., 01712345678): ").strip()
    if not phone.startswith("+88"):
        if phone.startswith("0"):
            phone = "+88" + phone
        else:
            phone = "+880" + phone
    return phone


async def run_cli(client):
    """Download Telegram links from the links file or interactive input."""
    links = []

    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
            if links:
                print(f"📄 Found {len(links)} links from {LINKS_FILE}")

    if not links:
        print(f"No links in {LINKS_FILE}. Paste Telegram Links (one per line).")
        print("Press Enter twice when finished.\n")
        while True:
            line = input().strip()
            if line == "":
                break
            links.append(line)

    if not links:
        print("No links provided. Exiting...")
        return

    print("\n🚀 Starting parallel downloads (CLI Mode)...\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    tasks = []

    for link in links:
        task = asyncio.create_task(download_link(client, link, semaphore))
        tasks.append(task)

    await asyncio.gather(*tasks)
    print("\n\n🎉 All CLI downloads finished.")


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

        for link_suffix in links:
            full_link = (
                f"https://{link_suffix}"
                if not link_suffix.startswith("http")
                else link_suffix
            )
            asyncio.create_task(process_bot_download(client, event, full_link, semaphore))

    async def process_bot_download(client, event, link, semaphore):
        status_message = await client.send_message("me", "⏳ Downloading...")

        download_reporter = TelegramStatusProgressReporter(
            status_message,
            action="Downloading",
        )
        token = set_status_progress_reporter(download_reporter)
        try:
            path = await download_link(client, link, semaphore)
        finally:
            reset_status_progress_reporter(token)
            download_reporter.stop()
            await download_reporter.wait()

        if not path:
            await status_message.edit("❌ Download failed")
            await asyncio.sleep(5)
            await status_message.delete()
            print(f"❌ Process failed for link: {link}")
            return

        file_name = os.path.basename(path)

        await status_message.edit("✅ Download complete")
        await asyncio.sleep(1)
        await status_message.edit("⏫ Uploading...")

        upload_reporter = TelegramStatusProgressReporter(
            status_message,
            action="Uploading",
        )
        token = set_status_progress_reporter(upload_reporter)
        try:
            await client.send_file(
                "me",
                path,
                progress_callback=ProgressCallback(file_name, action="Uploading"),
            )
        except Exception as e:
            upload_reporter.stop()
            await upload_reporter.wait()
            await status_message.edit("❌ Upload failed")
            await asyncio.sleep(5)
            await status_message.delete()
            print(f"❌ Upload failed for {file_name}: {e}")
            return
        finally:
            reset_status_progress_reporter(token)

        upload_reporter.stop()
        await upload_reporter.wait()

        await status_message.edit("✅ Upload complete")
        await asyncio.sleep(2)
        await status_message.delete()

        os.remove(path)
        print(f"✅ Auto-deleted from PC: {file_name}")

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

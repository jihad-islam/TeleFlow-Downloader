import argparse

from telethon import TelegramClient

from src.bot import run_bot
from src.cli import run_cli
from src.config import API_HASH, API_ID


def get_phone():
    """Read and normalize a Bangladeshi phone number for Telethon login."""
    phone = input("\nEnter your phone number (e.g., 01712345678): ").strip()
    if not phone.startswith("+88"):
        if phone.startswith("0"):
            phone = "+88" + phone
        else:
            phone = "+880" + phone
    return phone


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

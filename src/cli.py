import asyncio
import os
import time

from src.config import DOWNLOAD_FOLDER, LINKS_FILE, MAX_CONCURRENT_DOWNLOADS
from src.downloader import download_links_with_limit


SEPARATOR = "=" * 50


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
    start_time = time.monotonic()
    results = await download_links_with_limit(
        client,
        links,
        semaphore,
        MAX_CONCURRENT_DOWNLOADS,
    )
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

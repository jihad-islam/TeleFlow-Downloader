import sys
import time

from src.config import FAILED_LOG_FILE


def log_failed_link(link, error_msg):
    """Append failed links to a local log file for retry/debugging."""
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link} - Error: {error_msg}\n")


class ProgressCallback:
    """Terminal progress reporter compatible with Telethon callbacks."""

    def __init__(self, filename, action="Downloading"):
        self.filename = filename
        self.action = action
        self.start_time = time.time()
        self.last_print_time = 0

    def __call__(self, current, total):
        now = time.time()
        if now - self.last_print_time >= 1 or current == total:
            elapsed = now - self.start_time
            speed = current / elapsed if elapsed > 0 else 0
            percent = current * 100 / total if total else 0

            sys.stdout.write(
                f"\r[{self.action}] {self.filename[:20]}... | {percent:.2f}% | "
                f"{current/1024/1024:.2f}/{total/1024/1024:.2f} MB | "
                f"{speed/1024/1024:.2f} MB/s \033[K"
            )
            sys.stdout.flush()
            self.last_print_time = now

            if current == total:
                print()

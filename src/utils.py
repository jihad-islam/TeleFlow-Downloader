import asyncio
import contextvars
import sys
import time

from src.config import FAILED_LOG_FILE

_status_progress_reporter = contextvars.ContextVar(
    "status_progress_reporter",
    default=None,
)


def log_failed_link(link, error_msg):
    """Append failed links to a local log file for retry/debugging."""
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link} - Error: {error_msg}\n")


def set_status_progress_reporter(reporter):
    """Attach a Telegram status reporter to progress callbacks in this task."""
    return _status_progress_reporter.set(reporter)


def reset_status_progress_reporter(token):
    """Detach the Telegram status reporter from progress callbacks in this task."""
    _status_progress_reporter.reset(token)


class TelegramStatusProgressReporter:
    """Rate-limited Telegram status message updater for transfer progress."""

    def __init__(self, status_message, action, min_interval=60):
        self.status_message = status_message
        self.action = action
        self.min_interval = min_interval
        self.last_edit_time = 0
        self.edit_task = None
        self.active = True

    def set_action(self, action):
        self.action = action
        self.last_edit_time = 0

    def stop(self):
        self.active = False

    async def wait(self):
        if self.edit_task and not self.edit_task.done():
            await self.edit_task

    def update(self, filename, current, total, speed):
        if not self.active:
            return

        now = time.time()
        if now - self.last_edit_time < self.min_interval:
            return

        if self.edit_task and not self.edit_task.done():
            return

        percent = current * 100 / total if total else 0
        icon = "⏫" if self.action == "Uploading" else "⏳"
        text = (
            f"{icon} {self.action}...\n\n"
            f"{filename}\n\n"
            f"Progress: {percent:.0f}%\n"
            f"Size: {format_size(current)} / {format_size(total)}\n"
            f"Speed: {speed / 1024 / 1024:.1f} MB/s"
        )

        self.last_edit_time = now
        self.edit_task = asyncio.create_task(self._edit(text))

    async def _edit(self, text):
        if not self.active:
            return

        try:
            await self.status_message.edit(text)
        except Exception:
            pass


def format_size(size):
    """Format byte counts using compact binary units."""
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size or 0)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{value:.0f} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


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
            reporter = _status_progress_reporter.get()

            sys.stdout.write(
                f"\r[{self.action}] {self.filename[:20]}... | {percent:.2f}% | "
                f"{current/1024/1024:.2f}/{total/1024/1024:.2f} MB | "
                f"{speed/1024/1024:.2f} MB/s \033[K"
            )
            sys.stdout.flush()
            self.last_print_time = now
            if reporter:
                reporter.update(self.filename, current, total, speed)

            if current == total:
                print()

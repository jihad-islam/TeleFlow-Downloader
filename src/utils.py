import asyncio
import contextvars
import sys
import time

from src.config import FAILED_LOG_FILE

_status_progress_reporter = contextvars.ContextVar(
    "status_progress_reporter",
    default=None,
)
_terminal_progress_display = None


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

    def __init__(self, status_message, action, min_interval=5):
        self.status_message = status_message
        self.action = action
        self.min_interval = min_interval
        self.last_edit_time = 0
        self.edit_task = None
        self.active = True
        self.transfers = {}

    def set_action(self, action):
        self.action = action
        self.last_edit_time = 0
        self.transfers.clear()

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
        self.transfers[filename] = {
            "current": current,
            "total": total,
            "percent": percent,
            "speed": speed,
            "updated_at": now,
            "complete": current == total,
        }
        text = self._render_status(icon)

        self.last_edit_time = now
        self.edit_task = asyncio.create_task(self._edit(text))

    def _render_status(self, icon):
        transfers = sorted(
            self.transfers.items(),
            key=lambda item: item[1]["updated_at"],
            reverse=True,
        )
        active_transfers = [
            item for item in transfers if not item[1]["complete"]
        ]
        completed_count = len(transfers) - len(active_transfers)
        visible_transfers = (active_transfers or transfers)[:5]
        active_count = len(active_transfers)

        if active_count:
            file_label = "file" if active_count == 1 else "files"
            header = f"{icon} {self.action} {active_count} active {file_label}"
            if completed_count:
                header = f"{header}, {completed_count} done"
        else:
            header = f"{icon} {self.action} complete"

        lines = [header]

        for filename, state in visible_transfers:
            short_name = shorten_filename(filename, 42)
            lines.extend(
                [
                    "",
                    short_name,
                    (
                        f"{state['percent']:.0f}% | "
                        f"{format_size(state['current'])} / "
                        f"{format_size(state['total'])} | "
                        f"{state['speed'] / 1024 / 1024:.1f} MB/s"
                    ),
                ]
            )

        hidden_count = len(active_transfers) - len(visible_transfers)
        if hidden_count > 0:
            lines.extend(["", f"+ {hidden_count} more"])

        return "\n".join(lines)

    async def _edit(self, text):
        if not self.active:
            return

        try:
            await self.status_message.edit(text)
        except Exception:
            pass


def shorten_filename(filename, max_length):
    """Keep long filenames readable in terminal and Telegram status text."""
    if len(filename) <= max_length:
        return filename

    if max_length <= 3:
        return filename[:max_length]

    return f"{filename[: max_length - 3]}..."


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


class TerminalProgressDisplay:
    """Render a small fixed set of live progress lines in the terminal."""

    def __init__(self, max_lines=2):
        self.max_lines = max_lines
        self.transfers = {}
        self.rendered_lines = 0

    def update(self, key, action, filename, current, total, speed):
        percent = current * 100 / total if total else 0
        complete = current == total
        now = time.time()
        self.transfers[key] = {
            "action": action,
            "filename": filename,
            "current": current,
            "total": total,
            "percent": percent,
            "speed": speed,
            "updated_at": now,
            "complete": complete,
        }

        self._render()

        if complete:
            self.transfers.pop(key, None)
            if not self.transfers:
                self.rendered_lines = 0

    def _render(self):
        transfers = sorted(
            self.transfers.values(),
            key=lambda state: state["updated_at"],
            reverse=True,
        )
        visible_transfers = transfers[: self.max_lines]

        if self.rendered_lines:
            sys.stdout.write(f"\033[{self.rendered_lines}F")

        for state in visible_transfers:
            line = (
                f"[{state['action']}] "
                f"{shorten_filename(state['filename'], 42)} | "
                f"{state['percent']:.2f}% | "
                f"{format_size(state['current'])}/{format_size(state['total'])} | "
                f"{state['speed'] / 1024 / 1024:.2f} MB/s"
            )
            sys.stdout.write(f"{line}\033[K\n")

        for _ in range(self.rendered_lines - len(visible_transfers)):
            sys.stdout.write("\033[K\n")

        sys.stdout.flush()
        self.rendered_lines = len(visible_transfers)


def get_terminal_progress_display():
    """Return the shared terminal progress display."""
    global _terminal_progress_display

    if _terminal_progress_display is None:
        _terminal_progress_display = TerminalProgressDisplay()

    return _terminal_progress_display


class ProgressCallback:
    """Terminal progress reporter compatible with Telethon callbacks."""

    def __init__(self, filename, action="Downloading"):
        self.filename = filename
        self.action = action
        self.key = f"{action}:{filename}:{id(self)}"
        self.start_time = time.time()
        self.last_print_time = 0

    def __call__(self, current, total):
        now = time.time()
        if now - self.last_print_time >= 1 or current == total:
            elapsed = now - self.start_time
            speed = current / elapsed if elapsed > 0 else 0
            reporter = _status_progress_reporter.get()

            get_terminal_progress_display().update(
                self.key,
                self.action,
                self.filename,
                current,
                total,
                speed,
            )
            self.last_print_time = now
            if reporter:
                reporter.update(self.filename, current, total, speed)

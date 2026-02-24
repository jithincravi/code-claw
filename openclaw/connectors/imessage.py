"""iMessage connector for OpenClaw.

This connector works on macOS by:

* **Sending** – executing an AppleScript snippet via ``osascript`` to
  instruct the Messages app to dispatch a message.
* **Receiving** – polling the Messages SQLite database at
  ``~/Library/Messages/chat.db``, tracking the last-seen message row ID
  so it only processes genuinely new inbound messages.

.. note::
   Running OpenClaw with iMessage requires macOS with the Messages app
   signed in to an Apple ID or phone number.  The process needs Full Disk
   Access (or at minimum access to ``~/Library/Messages/chat.db``) which
   can be granted in *System Settings → Privacy & Security → Full Disk
   Access*.
"""

from __future__ import annotations

import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Callable

from openclaw.connectors.base import BaseConnector

# Path to the Messages SQLite database on macOS.
_CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"

# How often (seconds) to check for new messages when polling.
_POLL_INTERVAL = 2


def _send_imessage(recipient: str, message: str) -> None:
    """Deliver *message* to *recipient* via AppleScript / Messages.app."""
    # Escape double-quotes inside the message to keep the AppleScript valid.
    safe_message = message.replace('"', '\\"')
    script = (
        f'tell application "Messages"\n'
        f'  set targetService to 1st service whose service type = iMessage\n'
        f'  set targetBuddy to buddy "{recipient}" of targetService\n'
        f'  send "{safe_message}" to targetBuddy\n'
        f'end tell'
    )
    subprocess.run(["osascript", "-e", script], check=True)


class IMessageConnector(BaseConnector):
    """OpenClaw connector for iMessage.

    Args:
        assistant: Callable that accepts ``(message, conversation_id)``
            and returns a reply string.  Typically
            :meth:`openclaw.assistant.Assistant.chat`.
        db_path: Override the default path to ``chat.db`` (mainly for
            testing).
        poll_interval: Seconds between database polls (default 2).
    """

    def __init__(
        self,
        assistant: Callable[[str, str], str],
        db_path: Path | str | None = None,
        poll_interval: float = _POLL_INTERVAL,
    ) -> None:
        self._assistant = assistant
        self._db_path = Path(db_path) if db_path else _CHAT_DB
        self._poll_interval = poll_interval
        self._last_rowid: int = self._get_latest_rowid()

    # ------------------------------------------------------------------
    # BaseConnector implementation
    # ------------------------------------------------------------------

    def send(self, recipient: str, message: str) -> None:
        """Send *message* to *recipient* via Messages.app."""
        _send_imessage(recipient, message)

    def start_polling(self) -> None:
        """Block and continuously poll ``chat.db`` for new messages."""
        print(f"[iMessage] Polling {self._db_path} every {self._poll_interval}s …")
        while True:
            self._process_new_messages()
            time.sleep(self._poll_interval)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_latest_rowid(self) -> int:
        """Return the highest ``ROWID`` currently in the message table."""
        if not self._db_path.exists():
            return 0
        try:
            with sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True) as conn:
                row = conn.execute(
                    "SELECT MAX(ROWID) FROM message"
                ).fetchone()
                return row[0] or 0
        except sqlite3.OperationalError:
            return 0

    def _process_new_messages(self) -> None:
        """Fetch messages newer than ``_last_rowid`` and reply to each."""
        if not self._db_path.exists():
            return
        try:
            with sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True) as conn:
                rows = conn.execute(
                    """
                    SELECT m.ROWID, h.id, m.text
                    FROM message m
                    JOIN handle h ON m.handle_id = h.ROWID
                    WHERE m.ROWID > ?
                      AND m.is_from_me = 0
                      AND m.text IS NOT NULL
                    ORDER BY m.ROWID ASC
                    """,
                    (self._last_rowid,),
                ).fetchall()
        except sqlite3.OperationalError:
            return

        for rowid, sender, text in rows:
            self._last_rowid = rowid
            print(f"[iMessage] ← {sender}: {text!r}")
            try:
                reply = self._assistant(text, conversation_id=sender)
                self.send(sender, reply)
                print(f"[iMessage] → {sender}: {reply!r}")
            except Exception as exc:  # noqa: BLE001
                print(f"[iMessage] Error replying to {sender}: {exc}")

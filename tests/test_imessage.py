"""Tests for the iMessage connector."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw.connectors.imessage import IMessageConnector, _send_imessage


# ---------------------------------------------------------------------------
# Helper: create a minimal chat.db fixture
# ---------------------------------------------------------------------------

def _create_chat_db(path: Path, messages: list[dict]) -> None:
    """Create a bare-bones chat.db with a message and handle table."""
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS handle (
                ROWID INTEGER PRIMARY KEY,
                id    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS message (
                ROWID      INTEGER PRIMARY KEY,
                handle_id  INTEGER,
                text       TEXT,
                is_from_me INTEGER DEFAULT 0,
                FOREIGN KEY (handle_id) REFERENCES handle(ROWID)
            );
            """
        )
        for msg in messages:
            conn.execute(
                "INSERT INTO handle (id) VALUES (?)", (msg["sender"],)
            )
            handle_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO message (handle_id, text, is_from_me) VALUES (?, ?, ?)",
                (handle_id, msg["text"], msg.get("is_from_me", 0)),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# _send_imessage
# ---------------------------------------------------------------------------

class TestSendIMessage:
    def test_calls_osascript(self):
        with patch("subprocess.run") as mock_run:
            _send_imessage("+15551234567", "Hello!")
            mock_run.assert_called_once()
            cmd = mock_run.call_args.args[0]
            assert cmd[0] == "osascript"
            assert "+15551234567" in cmd[2]
            assert "Hello!" in cmd[2]

    def test_escapes_double_quotes(self):
        with patch("subprocess.run") as mock_run:
            _send_imessage("+1", 'Say "hi"')
            script = mock_run.call_args.args[0][2]
            assert '\\"hi\\"' in script


# ---------------------------------------------------------------------------
# IMessageConnector
# ---------------------------------------------------------------------------

class TestIMessageConnector:
    def test_send_delegates_to_osascript(self):
        assistant = MagicMock(return_value="reply")
        connector = IMessageConnector(
            assistant=assistant, db_path="/nonexistent/path"
        )
        with patch("subprocess.run") as mock_run:
            connector.send("+15559876543", "test message")
            mock_run.assert_called_once()

    def test_process_new_messages_calls_assistant(self, tmp_path):
        db = tmp_path / "chat.db"
        _create_chat_db(db, [{"sender": "+1555000", "text": "Hello bot"}])

        assistant = MagicMock(return_value="Hi there!")
        connector = IMessageConnector(assistant=assistant, db_path=db)
        # Force last_rowid to 0 so the seeded message is "new".
        connector._last_rowid = 0

        with patch.object(connector, "send") as mock_send:
            connector._process_new_messages()
            assistant.assert_called_once_with("Hello bot", conversation_id="+1555000")
            mock_send.assert_called_once_with("+1555000", "Hi there!")

    def test_ignores_own_messages(self, tmp_path):
        db = tmp_path / "chat.db"
        _create_chat_db(
            db, [{"sender": "+1555000", "text": "my msg", "is_from_me": 1}]
        )
        assistant = MagicMock(return_value="reply")
        connector = IMessageConnector(assistant=assistant, db_path=db)
        connector._last_rowid = 0

        with patch.object(connector, "send"):
            connector._process_new_messages()
            assistant.assert_not_called()

    def test_advances_last_rowid(self, tmp_path):
        db = tmp_path / "chat.db"
        _create_chat_db(db, [{"sender": "+1", "text": "msg1"}])
        assistant = MagicMock(return_value="ok")
        connector = IMessageConnector(assistant=assistant, db_path=db)
        connector._last_rowid = 0

        with patch.object(connector, "send"):
            connector._process_new_messages()

        assert connector._last_rowid > 0

    def test_missing_db_is_noop(self, tmp_path):
        assistant = MagicMock()
        connector = IMessageConnector(
            assistant=assistant, db_path=tmp_path / "missing.db"
        )
        connector._process_new_messages()  # should not raise
        assistant.assert_not_called()

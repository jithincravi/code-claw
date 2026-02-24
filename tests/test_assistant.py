"""Tests for the core Assistant class."""

from unittest.mock import MagicMock, patch

import pytest

from openclaw.assistant import Assistant


@pytest.fixture
def mock_openai_client():
    """Patch the OpenAI client so tests don't make real API calls."""
    with patch("openclaw.assistant.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        yield mock_client


def _make_response(text: str):
    """Build a minimal fake OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------

class TestChat:
    def test_returns_reply(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response(
            "Hello!"
        )
        assistant = Assistant(api_key="test-key")
        reply = assistant.chat("Hi")
        assert reply == "Hello!"

    def test_sends_system_prompt_first(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response("ok")
        assistant = Assistant(api_key="test-key", system_prompt="Be brief.")
        assistant.chat("hello", conversation_id="user1")

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be brief."}

    def test_different_conversation_ids_are_isolated(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response("ok")
        assistant = Assistant(api_key="test-key")
        assistant.chat("msg from user A", conversation_id="A")
        assistant.chat("msg from user B", conversation_id="B")

        # User B's history should only contain their own message.
        history_b = assistant._histories["B"]
        assert all(m["content"] != "msg from user A" for m in history_b)

    def test_history_accumulates(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response("ok")
        assistant = Assistant(api_key="test-key")
        assistant.chat("first", conversation_id="u")
        assistant.chat("second", conversation_id="u")

        history = assistant._histories["u"]
        # 2 user messages + 2 assistant replies
        assert len(history) == 4

    def test_history_trimmed_to_max(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response("r")
        assistant = Assistant(api_key="test-key", max_history=2)
        for i in range(5):
            assistant.chat(f"msg{i}", conversation_id="u")

        history = assistant._histories["u"]
        assert len(history) <= 4  # 2 pairs × 2 messages each


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_history(self, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = _make_response("ok")
        assistant = Assistant(api_key="test-key")
        assistant.chat("hello", conversation_id="u")
        assistant.reset("u")
        assert "u" not in assistant._histories

    def test_reset_unknown_id_is_noop(self, mock_openai_client):
        assistant = Assistant(api_key="test-key")
        assistant.reset("nonexistent")  # should not raise

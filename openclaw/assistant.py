"""Core AI assistant powered by the OpenAI Chat Completions API."""

from __future__ import annotations

from typing import List

from openai import OpenAI


class Assistant:
    """Stateful AI assistant that maintains per-user conversation history.

    Args:
        api_key: OpenAI API key.  Reads ``OPENAI_API_KEY`` from the
            environment when *None*.
        model: OpenAI chat model to use (default ``gpt-4o-mini``).
        system_prompt: Initial system instruction that shapes the
            assistant's personality and capabilities.
        max_history: Maximum number of *message pairs* (user + assistant)
            to keep in memory per conversation.  Older messages are dropped
            to stay within the model's context window.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are OpenClaw, a helpful personal AI assistant. "
        "Be concise, friendly and accurate."
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        system_prompt: str | None = None,
        max_history: int = 20,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.max_history = max_history
        # conversation_id -> list of {"role": ..., "content": ...}
        self._histories: dict[str, List[dict]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, message: str, conversation_id: str = "default") -> str:
        """Send *message* and return the assistant's reply.

        Args:
            message: The user's inbound text.
            conversation_id: Identifier that scopes conversation history
                (e.g. a phone number or iMessage handle).

        Returns:
            The assistant's reply as a plain string.
        """
        history = self._get_history(conversation_id)
        history.append({"role": "user", "content": message})

        messages = [{"role": "system", "content": self.system_prompt}] + history

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        reply = response.choices[0].message.content or ""

        history.append({"role": "assistant", "content": reply})
        self._trim_history(history)
        return reply

    def reset(self, conversation_id: str = "default") -> None:
        """Clear the conversation history for *conversation_id*."""
        self._histories.pop(conversation_id, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_history(self, conversation_id: str) -> List[dict]:
        if conversation_id not in self._histories:
            self._histories[conversation_id] = []
        return self._histories[conversation_id]

    def _trim_history(self, history: List[dict]) -> None:
        """Keep at most *max_history* pairs (2 × max_history messages)."""
        max_messages = self.max_history * 2
        if len(history) > max_messages:
            del history[: len(history) - max_messages]

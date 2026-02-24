"""Abstract base class for all OpenClaw messaging connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Common interface that every messaging connector must implement.

    Subclasses handle the platform-specific details of sending and
    receiving messages, while the :class:`~openclaw.assistant.Assistant`
    provides the AI responses.
    """

    @abstractmethod
    def send(self, recipient: str, message: str) -> None:
        """Send *message* to *recipient*.

        Args:
            recipient: Platform-specific address (phone number, handle…).
            message: Text body to deliver.
        """

    @abstractmethod
    def start_polling(self) -> None:
        """Begin listening for inbound messages and dispatch replies.

        Implementations may block (polling loop) or start a background
        thread / webhook server as appropriate.
        """

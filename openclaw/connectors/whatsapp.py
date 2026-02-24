"""WhatsApp connector for OpenClaw (powered by Twilio).

This connector uses the `Twilio Programmable Messaging API
<https://www.twilio.com/docs/whatsapp>`_ to:

* **Send** replies via the REST API.
* **Receive** inbound messages through a Twilio webhook handled by a
  lightweight Flask application (see :mod:`openclaw.server`).

Setup
-----
1. Create a Twilio account and obtain a WhatsApp-enabled number (or use
   the Twilio Sandbox for WhatsApp during development).
2. Set the following environment variables (or pass them directly)::

       TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       TWILIO_AUTH_TOKEN=your_auth_token
       TWILIO_WHATSAPP_NUMBER=+14155238886  # your Twilio WhatsApp number

3. Point your Twilio webhook to ``POST /whatsapp`` on a publicly
   reachable URL (e.g. via `ngrok <https://ngrok.com>`_ during
   development).
"""

from __future__ import annotations

import os
from typing import Callable

from twilio.rest import Client

from openclaw.connectors.base import BaseConnector

# Prefix required by Twilio for WhatsApp addresses.
_WA_PREFIX = "whatsapp:"


def _ensure_prefix(number: str) -> str:
    """Return *number* with the ``whatsapp:`` prefix if not already present."""
    return number if number.startswith(_WA_PREFIX) else f"{_WA_PREFIX}{number}"


class WhatsAppConnector(BaseConnector):
    """OpenClaw connector for WhatsApp via Twilio.

    Args:
        assistant: Callable ``(message, conversation_id) -> reply``.
            Typically :meth:`openclaw.assistant.Assistant.chat`.
        account_sid: Twilio account SID.  Falls back to
            ``TWILIO_ACCOUNT_SID`` env var.
        auth_token: Twilio auth token.  Falls back to
            ``TWILIO_AUTH_TOKEN`` env var.
        from_number: Your Twilio WhatsApp-enabled number (E.164 format,
            e.g. ``+14155238886``).  Falls back to
            ``TWILIO_WHATSAPP_NUMBER`` env var.
    """

    def __init__(
        self,
        assistant: Callable[[str, str], str],
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ) -> None:
        self._assistant = assistant
        _sid = account_sid or os.environ["TWILIO_ACCOUNT_SID"]
        _token = auth_token or os.environ["TWILIO_AUTH_TOKEN"]
        self._from_number = _ensure_prefix(
            from_number or os.environ["TWILIO_WHATSAPP_NUMBER"]
        )
        self._client = Client(_sid, _token)

    # ------------------------------------------------------------------
    # BaseConnector implementation
    # ------------------------------------------------------------------

    def send(self, recipient: str, message: str) -> None:
        """Send *message* to *recipient* via Twilio WhatsApp."""
        self._client.messages.create(
            from_=self._from_number,
            to=_ensure_prefix(recipient),
            body=message,
        )

    def start_polling(self) -> None:
        """Start the Flask webhook server to receive inbound messages.

        This delegates to :func:`openclaw.server.run_whatsapp_server`
        which creates a Flask app with a ``POST /whatsapp`` endpoint.
        Call this method to start the blocking web server.
        """
        from openclaw.server import run_whatsapp_server  # local import to avoid circular

        run_whatsapp_server(self)

    # ------------------------------------------------------------------
    # Webhook handler (called by server.py)
    # ------------------------------------------------------------------

    def handle_inbound(self, sender: str, body: str) -> str:
        """Process an inbound WhatsApp message and return the reply.

        Args:
            sender: The sender's WhatsApp number (with or without prefix).
            body: The text body of the inbound message.

        Returns:
            The AI-generated reply string.
        """
        conversation_id = sender
        print(f"[WhatsApp] ← {sender}: {body!r}")
        reply = self._assistant(body, conversation_id=conversation_id)
        self.send(sender, reply)
        print(f"[WhatsApp] → {sender}: {reply!r}")
        return reply

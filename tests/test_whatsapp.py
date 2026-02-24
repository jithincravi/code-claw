"""Tests for the WhatsApp connector and webhook server."""

from unittest.mock import MagicMock, patch

import pytest

from openclaw.connectors.whatsapp import WhatsAppConnector, _ensure_prefix
from openclaw.server import create_whatsapp_app


# ---------------------------------------------------------------------------
# _ensure_prefix
# ---------------------------------------------------------------------------

class TestEnsurePrefix:
    def test_adds_prefix_when_missing(self):
        assert _ensure_prefix("+15551234567") == "whatsapp:+15551234567"

    def test_does_not_double_prefix(self):
        assert _ensure_prefix("whatsapp:+15551234567") == "whatsapp:+15551234567"


# ---------------------------------------------------------------------------
# WhatsAppConnector
# ---------------------------------------------------------------------------

@pytest.fixture
def connector():
    """Create a WhatsAppConnector with a mocked Twilio client."""
    assistant = MagicMock(return_value="Assistant reply")
    with patch("openclaw.connectors.whatsapp.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        conn = WhatsAppConnector(
            assistant=assistant,
            account_sid="ACtest",
            auth_token="token",
            from_number="+14155238886",
        )
        conn._mock_twilio = mock_twilio
        conn._mock_assistant = assistant
        yield conn


class TestWhatsAppConnectorSend:
    def test_send_calls_twilio(self, connector):
        connector.send("+15559876543", "Hello!")
        connector._mock_twilio.messages.create.assert_called_once_with(
            from_="whatsapp:+14155238886",
            to="whatsapp:+15559876543",
            body="Hello!",
        )

    def test_send_already_prefixed_recipient(self, connector):
        connector.send("whatsapp:+15559876543", "Hi")
        call_kwargs = connector._mock_twilio.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+15559876543"


class TestWhatsAppConnectorHandleInbound:
    def test_handle_inbound_calls_assistant_and_sends(self, connector):
        with patch.object(connector, "send") as mock_send:
            reply = connector.handle_inbound(
                "whatsapp:+15550001111", "What is 2+2?"
            )
        connector._mock_assistant.assert_called_once_with(
            "What is 2+2?", conversation_id="whatsapp:+15550001111"
        )
        mock_send.assert_called_once_with(
            "whatsapp:+15550001111", "Assistant reply"
        )
        assert reply == "Assistant reply"


# ---------------------------------------------------------------------------
# Flask webhook server
# ---------------------------------------------------------------------------

class TestWhatsAppWebhookServer:
    @pytest.fixture
    def app(self, connector):
        app = create_whatsapp_app(connector)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_post_whatsapp_returns_empty_twiml(self, client, connector):
        with patch.object(connector, "handle_inbound"):
            resp = client.post(
                "/whatsapp",
                data={"From": "whatsapp:+1234", "Body": "Hello"},
            )
        assert resp.status_code == 200
        assert b"<Response></Response>" in resp.data

    def test_post_whatsapp_dispatches_to_connector(self, client, connector):
        with patch.object(connector, "handle_inbound") as mock_handle:
            client.post(
                "/whatsapp",
                data={"From": "whatsapp:+1234", "Body": "test"},
            )
        mock_handle.assert_called_once_with("whatsapp:+1234", "test")

    def test_missing_body_is_ignored(self, client, connector):
        with patch.object(connector, "handle_inbound") as mock_handle:
            resp = client.post("/whatsapp", data={"From": "whatsapp:+1234"})
        mock_handle.assert_not_called()
        assert resp.status_code == 200

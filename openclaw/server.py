"""Flask webhook server for the WhatsApp connector.

Twilio posts inbound WhatsApp messages to ``POST /whatsapp``.
This module provides a minimal Flask application that parses the
Twilio request and delegates to
:meth:`~openclaw.connectors.whatsapp.WhatsAppConnector.handle_inbound`.
"""

from __future__ import annotations

from flask import Flask, Response, request

from openclaw.connectors.whatsapp import WhatsAppConnector


def create_whatsapp_app(connector: WhatsAppConnector) -> Flask:
    """Return a configured Flask application for the WhatsApp webhook.

    Args:
        connector: The :class:`~openclaw.connectors.whatsapp.WhatsAppConnector`
            that will process inbound messages and send replies.

    Returns:
        A :class:`flask.Flask` instance with the ``POST /whatsapp`` route
        registered.
    """
    app = Flask(__name__)

    @app.route("/whatsapp", methods=["POST"])
    def whatsapp_webhook() -> Response:
        sender = request.form.get("From", "")
        body = request.form.get("Body", "")

        if sender and body:
            try:
                connector.handle_inbound(sender, body)
            except Exception as exc:  # noqa: BLE001
                print(f"[WhatsApp server] Error handling message: {exc}")

        # Return an empty TwiML response; the reply is sent via the REST API.
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            mimetype="text/xml",
        )

    return app


def run_whatsapp_server(
    connector: WhatsAppConnector,
    host: str = "0.0.0.0",
    port: int = 5000,
    debug: bool = False,
) -> None:
    """Create and run the Flask webhook server (blocking).

    Args:
        connector: The WhatsApp connector to dispatch messages to.
        host: Network interface to bind to (default ``0.0.0.0``).
        port: Port to listen on (default ``5000``).
        debug: Enable Flask debug mode (default ``False``).
    """
    app = create_whatsapp_app(connector)
    print(f"[WhatsApp server] Listening on {host}:{port}/whatsapp …")
    app.run(host=host, port=port, debug=debug)

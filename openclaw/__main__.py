"""CLI entry point for OpenClaw.

Usage::

    openclaw --connector imessage
    openclaw --connector whatsapp [--host 0.0.0.0] [--port 5000]

Environment variables are loaded from a ``.env`` file in the working
directory (via *python-dotenv*) before any connectors are initialised.
"""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="openclaw",
        description="Personal AI assistant controllable via iMessage or WhatsApp.",
    )
    parser.add_argument(
        "--connector",
        choices=["imessage", "whatsapp"],
        required=True,
        help="Messaging platform to connect to.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Override the default system prompt.",
    )
    # WhatsApp / webhook options
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for the WhatsApp webhook server (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the WhatsApp webhook server (default: 5000).",
    )

    args = parser.parse_args()

    from openclaw.assistant import Assistant

    assistant = Assistant(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model=args.model,
        system_prompt=args.system_prompt,
    )

    if args.connector == "imessage":
        from openclaw.connectors.imessage import IMessageConnector

        connector = IMessageConnector(assistant=assistant.chat)
        connector.start_polling()

    elif args.connector == "whatsapp":
        from openclaw.connectors.whatsapp import WhatsAppConnector

        connector = WhatsAppConnector(assistant=assistant.chat)
        from openclaw.server import run_whatsapp_server

        run_whatsapp_server(connector, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

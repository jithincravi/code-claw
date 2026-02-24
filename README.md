# OpenClaw – Personal AI Assistant

OpenClaw is a personal AI assistant that you can control from **iMessage** or **WhatsApp**.
It uses the [OpenAI Chat Completions API](https://platform.openai.com/docs/guides/chat) to
generate replies and maintains per-contact conversation history.

---

## Features

| Feature | iMessage | WhatsApp |
|---------|----------|----------|
| Send replies | ✅ AppleScript | ✅ Twilio REST API |
| Receive messages | ✅ Polls `chat.db` | ✅ Twilio webhook |
| Conversation memory | ✅ | ✅ |
| Custom system prompt | ✅ | ✅ |
| Any OpenAI model | ✅ | ✅ |

---

## Requirements

* Python 3.10+
* An [OpenAI API key](https://platform.openai.com/account/api-keys)
* **iMessage** – macOS with Messages.app signed in + Full Disk Access granted to the
  terminal / Python process
* **WhatsApp** – a [Twilio account](https://www.twilio.com/) with a WhatsApp-enabled
  number (the free Sandbox works great for testing)

---

## Installation

```bash
git clone https://github.com/jithincravi/code-claw.git
cd code-claw
pip install -r requirements.txt
# or, for development tools:
pip install -r requirements-dev.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```dotenv
# .env

# --- OpenAI ---
OPENAI_API_KEY=sk-...

# --- Twilio (WhatsApp only) ---
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
```

---

## Usage

### iMessage (macOS only)

```bash
python -m openclaw --connector imessage
```

OpenClaw will poll `~/Library/Messages/chat.db` every 2 seconds for new inbound
messages and reply via Messages.app using AppleScript.

> **Tip:** Grant your terminal Full Disk Access in
> *System Settings → Privacy & Security → Full Disk Access*.

### WhatsApp

```bash
python -m openclaw --connector whatsapp
```

This starts a Flask webhook server on port 5000.  Point your Twilio WhatsApp webhook
to `POST https://<your-host>/whatsapp`.

During local development, expose the server with
[ngrok](https://ngrok.com):

```bash
ngrok http 5000
# then set https://<ngrok-url>/whatsapp as the webhook URL in Twilio
```

#### Options

```
openclaw --connector imessage
openclaw --connector whatsapp [--host 0.0.0.0] [--port 5000]
                              [--model gpt-4o-mini]
                              [--system-prompt "You are my personal assistant."]
```

---

## Project structure

```
openclaw/
  __init__.py
  __main__.py          # CLI entry point
  assistant.py         # Core AI assistant (OpenAI)
  server.py            # Flask webhook server for WhatsApp
  connectors/
    __init__.py
    base.py            # Abstract connector interface
    imessage.py        # iMessage connector (AppleScript + chat.db)
    whatsapp.py        # WhatsApp connector (Twilio)
tests/
  test_assistant.py
  test_imessage.py
  test_whatsapp.py
```

---

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## License

MIT
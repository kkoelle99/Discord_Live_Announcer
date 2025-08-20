# Twitch Live Announcer Discord Bot

A Discord bot that announces when tracked Twitch streamers go live. Supports multiple streamers per server, custom alert messages, and optional role pings.

---

## Features

* Track multiple Twitch streamers per server
* Send live alerts to a specified text channel
* Optional role mentions when a streamer goes live
* Customizable alert messages with placeholders:

  * `{streamer}` → Twitch username
  * `{game}` → Game being played
  * `{title}` → Stream title
  * `{url}` → Twitch stream link
* Prevents duplicate alerts per live session
* Twitch API error handling with automatic retries

---

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/twitch-live-announcer.git
cd twitch-live-announcer
```

2. **Create a virtual environment** (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
python -m pip install -r requirements.txt
```

4. **Create a `.env` file** with your credentials:

```
DISCORD_TOKEN=your_discord_bot_token
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
```

5. **Start the bot**

```bash
python bot.py
```

---

## Commands

| Command                          | Description                                  |
| -------------------------------- | -------------------------------------------- |
| `!set_channel #channel`          | Set the channel for live alerts              |
| `!add_streamer streamer_name`    | Add a Twitch streamer to track               |
| `!remove_streamer streamer_name` | Remove a tracked streamer                    |
| `!list_streamers`                | Show currently tracked streamers             |
| `!set_role @Role`                | Set a role to mention when someone goes live |
| `!clear_role`                    | Remove role mentions                         |
| `!set_message custom message`    | Set a custom alert message with placeholders |

---

## Example Custom Message

```
!set_message {streamer} just went live playing {game}! Watch here: {url}
```

---

## Notes

* Make sure `config.json` is added to `.gitignore` to keep server-specific data private.
* The bot checks Twitch every minute.

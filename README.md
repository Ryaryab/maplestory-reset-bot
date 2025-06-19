# MapleStory Reset Bot

A Discord bot for tracking MapleStory daily and weekly resets, with auto-reminders and slash command support.  
Runs 24/7 on Railway!

## Features

- Slash commands to add, edit, and delete daily/weekly resets
- Two persistent messages for daily and weekly resets
- Automatic reset reminders (with @here ping)
- Clean, modern embeds with a pastel pink theme

## Usage

Invite the bot to your server and use the following slash commands:

- `/adddailyreset` — Add a daily reset task
- `/addweeklyreset` — Add a weekly reset task
- `/deletereset` — Delete a reset task by name
- `/editreset` — Edit a reset task by name

## Deploying

- Python 3.10+
- [discord.py](https://github.com/Rapptz/discord.py)
- [pytz](https://pypi.org/project/pytz/)

To deploy yourself, set a `DISCORD_TOKEN` environment variable with your bot token.

## Credits

- Built by Ryan Bradley
- Powered by OpenAI GPT and Railway

## License

MIT License (see [LICENSE](LICENSE))

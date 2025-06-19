import os
import json
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, timedelta
import pytz
import re

GUILD_ID = 1005491315879977011
RESET_CHANNEL_ID = 1385102082792493116
REMINDER_CHANNEL_ID = 1385133408442650725

DAILY_FILE = "daily_message.txt"
WEEKLY_FILE = "weekly_message.txt"
RESETS_FILE = "resets.json"

PASTEL_PINK = 0xF8C8DC

intents = discord.Intents.default()

def load_resets():
    if not os.path.exists(RESETS_FILE):
        return {"daily": [], "weekly": []}
    with open(RESETS_FILE, "r") as f:
        return json.load(f)

def save_resets(data):
    with open(RESETS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def compute_timestamp(time_str, freq, day_of_week=None):
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    hour, minute = map(int, time_str.split(":"))
    base = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if freq == "daily":
        if base <= now:
            base += timedelta(days=1)
    elif freq == "weekly":
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target = days.index(day_of_week.lower())
        current = now.weekday()
        delta = (target - current) % 7
        if delta == 0 and base <= now:
            delta = 7
        base += timedelta(days=delta)
    return int(base.timestamp())

def sanitize_emoji(emoji):
    if not emoji:
        return ""
    if re.match(r"^<a?:\w+:\d+>$", emoji):
        return emoji
    if emoji.startswith(":") and emoji.endswith(":"):
        return emoji
    try:
        emoji.encode("utf-8")
        return emoji
    except:
        return ""

def format_daily_embed(data):
    reset_time = compute_timestamp("20:00", "daily")
    embed = discord.Embed(
        title=f"<a:MaplestoryMushroom:1385184240643084441> __DAILY RESET__ — <t:{reset_time}:R>",
        color=PASTEL_PINK
    )
    for r in data:
        name = r["name"].strip()
        emoji = f"{r['emoji']} " if r["emoji"] else ""
        display_name = f"{emoji}{name}"
        if name.lower() == "ursus":
            ts1 = compute_timestamp("14:00", "daily")
            ts2 = compute_timestamp("21:00", "daily")
            embed.add_field(name=f"**{display_name}**", value=f"<t:{ts1}:R> <t:{ts2}:R>", inline=False)
        else:
            embed.add_field(name=f"**{display_name}**", value="\u200b", inline=False)
    return embed

def format_weekly_embed(data):
    embed = discord.Embed(
        title="<a:MaplestoryMushroom:1385184240643084441> __WEEKLY RESETS__",
        color=PASTEL_PINK
    )
    for r in data:
        emoji = f"{r['emoji']} " if r['emoji'] else ""
        ts = f"<t:{r['timestamp']}:R>"
        embed.add_field(name=f"{emoji}**{r['name']}**", value=ts, inline=False)
    return embed

def format_daily_reminder(data):
    embed = discord.Embed(
        title="⏰ **Daily Reset Reminder!**",
        color=PASTEL_PINK
    )
    for r in data:
        emoji = f"{r['emoji']} " if r["emoji"] else ""
        name = r["name"]
        if name.lower() == "ursus":
            ts1 = compute_timestamp("14:00", "daily")
            ts2 = compute_timestamp("21:00", "daily")
            embed.add_field(name=f"{emoji}**{name}**", value=f"<t:{ts1}:t> & <t:{ts2}:t> (EST)", inline=False)
        else:
            embed.add_field(name=f"{emoji}**{name}**", value="Don't forget to clear!", inline=False)
    return embed

def get_reminder_channel(bot):
    return bot.get_channel(REMINDER_CHANNEL_ID)

# Track when we've already sent a reminder to avoid duplicates
reminder_state = {
    "daily": None,
    "weekly": {}  # key: (name, hours), value: last_sent_timestamp
}

class MapleBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"✅ Synced {len(synced)} commands to {GUILD_ID}")
        for cmd in synced:
            print(f"  - {cmd.name}")

        daily_reminder.start(self)
        weekly_reminder.start(self)

bot = MapleBot()

# -------------- COMMANDS --------------

@bot.tree.command(name="adddailyreset", description="Add a daily MapleStory reset")
@app_commands.describe(name="The name of the daily reset task", emoji="Optional emoji")
async def adddailyreset(interaction: discord.Interaction, name: str, emoji: str = ""):
    name = name.strip()
    emoji = sanitize_emoji(emoji)
    data = load_resets()
    data["daily"].append({"name": name, "emoji": emoji})
    save_resets(data)

    channel = bot.get_channel(RESET_CHANNEL_ID)
    embed = format_daily_embed(data["daily"])

    if os.path.exists(DAILY_FILE):
        with open(DAILY_FILE, "r") as f:
            msg_id = int(f.read().strip())
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
        except:
            msg = await channel.send(embed=embed)
            with open(DAILY_FILE, "w") as f:
                f.write(str(msg.id))
    else:
        msg = await channel.send(embed=embed)
        with open(DAILY_FILE, "w") as f:
            f.write(str(msg.id))

    await interaction.response.send_message(f"✅ Added `{name}` to daily resets!", ephemeral=True)

@bot.tree.command(name="addweeklyreset", description="Add a weekly MapleStory reset")
@app_commands.describe(
    name="The name of the weekly reset task",
    time="Time of day in 24-hour format (HH:MM)",
    day="Day of the week it resets",
    emoji="Optional emoji"
)
async def addweeklyreset(interaction: discord.Interaction, name: str, time: str, day: str, emoji: str = ""):
    name = name.strip()
    emoji = sanitize_emoji(emoji)
    try:
        timestamp = compute_timestamp(time, "weekly", day)
    except Exception as e:
        return await interaction.response.send_message(f"❌ Error parsing time/day: {e}", ephemeral=True)

    data = load_resets()
    data["weekly"].append({"name": name, "time": time, "timestamp": timestamp, "emoji": emoji, "day": day})
    save_resets(data)

    channel = bot.get_channel(RESET_CHANNEL_ID)
    embed = format_weekly_embed(data["weekly"])

    if os.path.exists(WEEKLY_FILE):
        with open(WEEKLY_FILE, "r") as f:
            msg_id = int(f.read().strip())
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
        except:
            msg = await channel.send(embed=embed)
            with open(WEEKLY_FILE, "w") as f:
                f.write(str(msg.id))
    else:
        msg = await channel.send(embed=embed)
        with open(WEEKLY_FILE, "w") as f:
            f.write(str(msg.id))

    await interaction.response.send_message(f"✅ Added `{name}` to weekly resets!", ephemeral=True)

@bot.tree.command(name="deletereset", description="Delete a reset task by name (daily or weekly)")
@app_commands.describe(name="The name of the reset task to delete")
async def deletereset(interaction: discord.Interaction, name: str):
    name = name.strip()
    data = load_resets()
    deleted_from = None

    for i, r in enumerate(data["daily"]):
        if r["name"].lower() == name.lower():
            del data["daily"][i]
            deleted_from = "daily"
            break

    if not deleted_from:
        for i, r in enumerate(data["weekly"]):
            if r["name"].lower() == name.lower():
                del data["weekly"][i]
                deleted_from = "weekly"
                break

    if not deleted_from:
        return await interaction.response.send_message(f"❌ No reset named `{name}` found.", ephemeral=True)

    save_resets(data)
    channel = bot.get_channel(RESET_CHANNEL_ID)

    if deleted_from == "daily":
        if os.path.exists(DAILY_FILE):
            with open(DAILY_FILE, "r") as f:
                msg_id = int(f.read().strip())
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=format_daily_embed(data["daily"]))
            except:
                pass
    else:
        if os.path.exists(WEEKLY_FILE):
            with open(WEEKLY_FILE, "r") as f:
                msg_id = int(f.read().strip())
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=format_weekly_embed(data["weekly"]))
            except:
                pass

    await interaction.response.send_message(f"🗑️ `{name}` deleted from {deleted_from} resets.", ephemeral=True)

@bot.tree.command(name="editreset", description="Edit a reset task by name (daily or weekly)")
@app_commands.describe(
    name="The name of the reset task to edit",
    new_name="The new name (leave empty to keep the same)",
    new_time="New time for weekly reset (24-hour HH:MM, required if weekly)",
    new_day="New day of the week (required if weekly)",
    new_emoji="New emoji (optional)"
)
async def editreset(interaction: discord.Interaction, name: str, new_name: str = "", new_time: str = "", new_day: str = "", new_emoji: str = ""):
    name = name.strip()
    new_name = new_name.strip()
    new_emoji = sanitize_emoji(new_emoji)
    data = load_resets()
    edited = False

    for r in data["daily"]:
        if r["name"].lower() == name.lower():
            if new_name:
                r["name"] = new_name
            if new_emoji:
                r["emoji"] = new_emoji
            edited = "daily"
            break

    if not edited:
        for r in data["weekly"]:
            if r["name"].lower() == name.lower():
                if new_name:
                    r["name"] = new_name
                if new_emoji:
                    r["emoji"] = new_emoji
                if new_time and new_day:
                    try:
                        r["timestamp"] = compute_timestamp(new_time, "weekly", new_day)
                        r["time"] = new_time
                        r["day"] = new_day
                    except Exception as e:
                        return await interaction.response.send_message(f"❌ Time/day error: {e}", ephemeral=True)
                edited = "weekly"
                break

    if not edited:
        return await interaction.response.send_message(f"❌ No reset named `{name}` found.", ephemeral=True)

    save_resets(data)
    channel = bot.get_channel(RESET_CHANNEL_ID)

    if edited == "daily":
        if os.path.exists(DAILY_FILE):
            with open(DAILY_FILE, "r") as f:
                msg_id = int(f.read().strip())
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=format_daily_embed(data["daily"]))
            except:
                pass
    else:
        if os.path.exists(WEEKLY_FILE):
            with open(WEEKLY_FILE, "r") as f:
                msg_id = int(f.read().strip())
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=format_weekly_embed(data["weekly"]))
            except:
                pass

    await interaction.response.send_message(f"✏️ `{name}` updated successfully in {edited} resets!", ephemeral=True)

# -------------- REMINDERS --------------

@tasks.loop(seconds=30)
async def daily_reminder(bot):
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    data = load_resets()
    reset_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
    reminder_time = reset_time - timedelta(hours=2)  # 6 PM EST

    daystr = now.strftime("%Y-%m-%d")
    if now >= reminder_time and now < reminder_time + timedelta(minutes=1):
        if reminder_state["daily"] != daystr:
            channel = get_reminder_channel(bot)
            embed = format_daily_reminder(data["daily"])
            await channel.send(content='@here', embed=embed)  # Pings @here
            reminder_state["daily"] = daystr
    if now >= reset_time + timedelta(minutes=1):
        if reminder_state["daily"] == daystr:
            reminder_state["daily"] = None

@tasks.loop(seconds=30)
async def weekly_reminder(bot):
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    data = load_resets()
    channel = get_reminder_channel(bot)

    for r in data["weekly"]:
        reset_ts = r["timestamp"]
        reset_time = datetime.fromtimestamp(reset_ts, est)
        for hours in [48, 24]:
            reminder_ts = reset_time - timedelta(hours=hours)
            flag_key = (r["name"], hours)
            window_start = reminder_ts
            window_end = reminder_ts + timedelta(minutes=5)
            nowstr = now.strftime("%Y-%m-%d-%H")
            if now >= window_start and now < window_end:
                if reminder_state["weekly"].get(flag_key) != nowstr:
                    embed = discord.Embed(
                        title=f"⏰ **Weekly Reset Reminder!**",
                        description=f"{r['emoji']+' ' if r['emoji'] else ''}**{r['name']}** resets in <t:{reset_ts}:R> ({r['day'].capitalize()} at {r['time']} EST)",
                        color=PASTEL_PINK
                    )
                    await channel.send(content='@here', embed=embed)  # Pings @here
                    reminder_state["weekly"][flag_key] = nowstr
            if now >= window_end and reminder_state["weekly"].get(flag_key) == nowstr:
                reminder_state["weekly"][flag_key] = None

# -------------- BOT LAUNCH --------------

TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not daily_reminder.is_running():
        daily_reminder.start(bot)
    if not weekly_reminder.is_running():
        weekly_reminder.start(bot)

bot.run(TOKEN)

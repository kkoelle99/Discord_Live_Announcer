import discord
from discord.ext import commands, tasks
import aiohttp
import json
import asyncio
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

CONFIG_FILE = "config.json"
CONFIG = {}

# ---------------- CONFIG HANDLING ----------------
def load_config():
    global CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        CONFIG = {}

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG, f, indent=4)

# ---------------- BOT SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track who is currently live to avoid duplicate posts
CURRENTLY_LIVE = {}

# ---------------- TWITCH AUTH ----------------
async def get_twitch_oauth():
    async with aiohttp.ClientSession() as session:
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            return data.get("access_token")

# ---------------- TWITCH CHECK (with retries) ----------------
async def check_streamer_live(streamer, token, retries=3, delay=2):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.twitch.tv/helix/streams"
                headers = {
                    "Client-ID": TWITCH_CLIENT_ID,
                    "Authorization": f"Bearer {token}"
                }
                params = {"user_login": streamer}
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        raise Exception(f"Twitch API returned status {resp.status}")
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0]  # Stream is live
                    return None
        except Exception as e:
            print(f"Error checking {streamer}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                return None

# ---------------- TASK LOOP ----------------
@tasks.loop(minutes=1)
async def stream_checker():
    token = await get_twitch_oauth()
    for guild_id, cfg in CONFIG.items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue

        channel_id = cfg.get("channel_id")
        if not channel_id:
            continue
        channel = guild.get_channel(int(channel_id))
        if not channel:
            continue

        mention_role = cfg.get("mention_role")
        custom_msg = cfg.get("custom_message")
        for streamer in cfg.get("streamers", []):
            live_data = await check_streamer_live(streamer, token)
            was_live = CURRENTLY_LIVE.get(f"{guild_id}-{streamer}", False)

            if live_data and not was_live:
                # New live alert
                CURRENTLY_LIVE[f"{guild_id}-{streamer}"] = True
                title = live_data["title"]
                game = live_data.get("game_name", "Unknown")
                url = f"https://twitch.tv/{streamer}"

                embed = discord.Embed(
                    title=f"{streamer} is LIVE!",
                    description=title,
                    color=discord.Color.purple(),
                    url=url
                )
                embed.add_field(name="Game", value=game)
                embed.set_thumbnail(url=live_data["thumbnail_url"].replace("{width}", "128").replace("{height}", "128"))

                # Compose message
                if custom_msg:
                    content = custom_msg.format(streamer=streamer, game=game, title=title, url=url)
                    if mention_role:
                        content = f"<@&{mention_role}> {content}"
                else:
                    content = f"<@&{mention_role}>" if mention_role else None

                await channel.send(content=content, embed=embed)

            if not live_data and was_live:
                # Stream went offline
                CURRENTLY_LIVE[f"{guild_id}-{streamer}"] = False

# ---------------- COMMANDS ----------------
@bot.command()
async def set_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    CONFIG.setdefault(guild_id, {"channel_id": None, "streamers": [], "mention_role": None, "custom_message": None})
    CONFIG[guild_id]["channel_id"] = channel.id
    save_config()
    await ctx.send(f"Alerts will now be sent to {channel.mention}.")

@bot.command()
async def add_streamer(ctx, streamer: str):
    guild_id = str(ctx.guild.id)
    CONFIG.setdefault(guild_id, {"channel_id": None, "streamers": [], "mention_role": None, "custom_message": None})
    streamer = streamer.lower()
    if streamer not in CONFIG[guild_id]["streamers"]:
        CONFIG[guild_id]["streamers"].append(streamer)
        save_config()
        await ctx.send(f"Added streamer **{streamer}** to alerts.")
    else:
        await ctx.send("That streamer is already being tracked.")

@bot.command()
async def remove_streamer(ctx, streamer: str):
    guild_id = str(ctx.guild.id)
    streamer = streamer.lower()
    if guild_id in CONFIG and streamer in CONFIG[guild_id]["streamers"]:
        CONFIG[guild_id]["streamers"].remove(streamer)
        save_config()
        await ctx.send(f"Removed streamer **{streamer}** from alerts.")
    else:
        await ctx.send("That streamer is not being tracked.")

@bot.command()
async def list_streamers(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in CONFIG and CONFIG[guild_id]["streamers"]:
        await ctx.send("Currently tracking: " + ", ".join(CONFIG[guild_id]["streamers"]))
    else:
        await ctx.send("No streamers are being tracked.")

@bot.command()
async def set_role(ctx, role: discord.Role):
    guild_id = str(ctx.guild.id)
    CONFIG.setdefault(guild_id, {"channel_id": None, "streamers": [], "mention_role": None, "custom_message": None})
    CONFIG[guild_id]["mention_role"] = role.id
    save_config()
    await ctx.send(f"I will now mention {role.mention} when a streamer goes live.")

@bot.command()
async def clear_role(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in CONFIG:
        CONFIG[guild_id]["mention_role"] = None
        save_config()
        await ctx.send("Role mentions cleared. Alerts will now be sent without pings.")
    else:
        await ctx.send("No role mention was set.")

@bot.command()
async def set_message(ctx, *, message: str):
    guild_id = str(ctx.guild.id)
    CONFIG.setdefault(guild_id, {"channel_id": None, "streamers": [], "mention_role": None, "custom_message": None})
    CONFIG[guild_id]["custom_message"] = message
    save_config()
    await ctx.send(f"Custom alert message set:\n{message}")

# ---------------- STARTUP ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_config()
    stream_checker.start()

bot.run(DISCORD_TOKEN)

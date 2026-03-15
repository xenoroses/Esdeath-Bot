import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from flask import Flask
from threading import Thread
import asyncio
import sys
import socket
import time

# --- 1. AGGRESSIVE NETWORK WARM-UP & DNS BYPASS ---
def get_discord_connection_info(hostname="discord.com", retries=10):
    print(f"Pre-flight check: Resolving {hostname}...")
    
    # Probing stable IPs to wake up the container's network interface
    check_hosts = ["8.8.8.8", "google.com"]
    for host in check_hosts:
        for i in range(2):
            try:
                socket.gethostbyname(host)
                print(f"Network Check: {host} is reachable.")
                break
            except socket.gaierror:
                print(f"Waiting for network... ({host} attempt {i+1})")
                time.sleep(2)

    # Attempt dynamic resolution for discord.com
    for i in range(retries):
        try:
            ip = socket.gethostbyname(hostname)
            print(f"SUCCESS: {hostname} resolved to {ip}")
            return ip
        except socket.gaierror:
            print(f"DNS attempt {i+1} failed for {hostname}. Retrying...")
            time.sleep(3)
    
    # FINAL FALLBACK: Hardcoded Discord API IP (Cloudflare/Anycast)
    # This bypasses the Hugging Face DNS failure entirely
    fallback_ip = "162.159.138.232"
    print(f"CRITICAL: DNS Resolution failed. Using Hardcoded Fallback IP: {fallback_ip}")
    return fallback_ip

# Execute warmup and get target IP before initialization
TARGET_IP = get_discord_connection_info()

# --- 2. WEB SERVER SETUP (For Hugging Face Keep-Alive) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive and guarding Hugging Face."

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    print("Starting Web Server Thread...")
    t = Thread(target=run_flask)
    t.daemon = True 
    t.start()

# --- 3. BOT INITIALIZATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")

async def get_server_prefixes(bot, message):
    default_prefixes = ["!", "esdeath ", "es "]
    if not message.guild or not getattr(bot, 'redis', None):
        return commands.when_mentioned_or(*default_prefixes)(bot, message)
    try:
        cached_prefixes = await bot.redis.get(f"prefixes:{message.guild.id}")
        if cached_prefixes:
            if isinstance(cached_prefixes, bytes):
                cached_prefixes = cached_prefixes.decode('utf-8')
            custom_prefixes = json.loads(cached_prefixes)
            return commands.when_mentioned_or(*custom_prefixes)(bot, message)
    except Exception as e:
        print(f"Prefix Fetch Error: {e}")
    return commands.when_mentioned_or(*default_prefixes)(bot, message)

class EsdeathBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Stalking Zen"),
            help_command=None
        )
        self.redis = None

    async def setup_hook(self):
        print("--- SETUP HOOK STARTING ---")
        try:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                print("Redis Connected successfully.")
            else:
                print("REDIS ERROR: Missing Environment Variables.")
        except Exception as e:
            print(f"REDIS WARNING: Connection failed. Error: {e}")

        extensions = ["cogs.staff_cmds", "cogs.ai_chat"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Successfully loaded {ext}")
            except Exception as e:
                print(f"CRITICAL: Failed to load {ext} -> {e}")

        try:
            await self.tree.sync()
            print("--- SLASH COMMANDS SYNCED ---")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"SUCCESS: {self.user} is online and operational on Hugging Face.")

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You forgot an argument.", ephemeral=True)
        else:
            print(f"Unhandled Command Error: {error}")

# --- 4. STARTUP LOGIC ---
if __name__ == "__main__":
    keep_alive()
    
    if TOKEN:
        print(f"Initiating Discord Login (Targeting IP: {TARGET_IP})...")
        bot = EsdeathBot()
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"FATAL ERROR ON STARTUP: {e}")
            sys.exit(1)
    else:
        print("FATAL ERROR: dc_token missing!")
        sys.exit(1)
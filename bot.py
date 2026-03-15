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

# --- 1. NETWORK WARM-UP (FIX FOR HUGGING FACE DNS ERRORS) ---
def warmup_dns(hostname="discord.com", retries=5):
    print(f"Pre-flight check: Resolving {hostname}...")
    for i in range(retries):
        try:
            ip = socket.gethostbyname(hostname)
            print(f"Successfully resolved {hostname} to {ip}")
            return True
        except socket.gaierror:
            print(f"DNS attempt {i+1} failed. Retrying in 2 seconds...")
            time.sleep(2)
    return False

# Run the warmup before anything else
warmup_dns()

# 2. Web Server Setup (Updated for Hugging Face Port 7860)
app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive and guarding Hugging Face."

def run_flask():
    # Hugging Face Spaces default to 7860
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    print("Starting Web Server Thread...")
    t = Thread(target=run_flask)
    t.daemon = True 
    t.start()

# 3. Bot Initialization
load_dotenv()
TOKEN = os.getenv("dc_token")

# --- Dynamic Prefix Fetcher ---
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
        pass
        
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
        
        # Connect to Redis
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

        # Load Cogs
        extensions = ["cogs.staff_cmds", "cogs.ai_chat"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Successfully loaded {ext}")
            except Exception as e:
                print(f"CRITICAL: Failed to load {ext} -> {e}")

        # Sync Slash Commands
        try:
            await self.tree.sync()
            print("--- SLASH COMMANDS SYNCED ---")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"SUCCESS: {self.user} is online and operational on Hugging Face.")

    # --- THE GLOBAL ERROR HANDLER ---
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("You forgot an argument. Use the command properly.", ephemeral=True)
            
        elif isinstance(error, commands.MemberNotFound) or isinstance(error, commands.UserNotFound):
            return await ctx.send("I can't find that user. Make sure you are providing a valid ID or tag.", ephemeral=True)
            
        elif isinstance(error, commands.HybridCommandError):
            return await ctx.send("I can't process that input. Double-check your formatting.", ephemeral=True)
            
        else:
            print(f"Unhandled Command Error: {error}")

# 4. Startup Logic
if __name__ == "__main__":
    keep_alive()
    
    if TOKEN:
        bot = EsdeathBot()
        print("Initiating Discord Login...")
        bot.run(TOKEN)
    else:
        print("FATAL ERROR: dc_token missing!")
        sys.exit(1)
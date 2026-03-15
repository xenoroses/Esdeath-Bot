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

# 1. Web Server Setup (To satisfy Render's port binding)
app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    print("Starting Web Server Thread...")
    t = Thread(target=run_flask)
    t.daemon = True  # CRITICAL FIX: This prevents Flask from hanging the main bot process
    t.start()

# 2. Bot Initialization
load_dotenv()
TOKEN = os.getenv("dc_token")

# --- NEW: Dynamic Prefix Fetcher ---
async def get_server_prefixes(bot, message):
    # The default prefixes if a server hasn't set custom ones
    default_prefixes = ["!", "esdeath ", "es "]
    
    # DMs don't have a guild, or if Redis is offline, use the defaults
    if not message.guild or not getattr(bot, 'redis', None):
        return commands.when_mentioned_or(*default_prefixes)(bot, message)
        
    try:
        # Check Upstash Redis for a custom prefix list for this specific server
        cached_prefixes = await bot.redis.get(f"prefixes:{message.guild.id}")
        if cached_prefixes:
            # Decode the JSON list stored in Redis
            if isinstance(cached_prefixes, bytes):
                cached_prefixes = cached_prefixes.decode('utf-8')
            custom_prefixes = json.loads(cached_prefixes)
            return commands.when_mentioned_or(*custom_prefixes)(bot, message)
    except Exception as e:
        print(f"Prefix Fetch Error: {e}")
        pass # If Redis fails to parse, just fall back to the defaults
        
    return commands.when_mentioned_or(*default_prefixes)(bot, message)

class EsdeathBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_server_prefixes, # <-- Now using the dynamic fetcher
            intents=intents,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Stalking Zen")
        )
        self.redis = None

    async def setup_hook(self):
        print("--- SETUP HOOK STARTING ---")
        
        # 1. Connect to Redis (Non-blocking with timeout)
        print("Attempting Redis connection...")
        try:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            
            if url and token:
                self.redis = Redis(url=url, token=token)
                # Quick ping to see if Cloudflare blocks us
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                print("Redis Connected successfully.")
            else:
                print("REDIS ERROR: Missing Environment Variables.")
        except Exception as e:
            print(f"REDIS WARNING: Connection failed or timed out. AI memory disabled. Error: {e}")

        # 2. Load Cogs
        extensions = ["cogs.staff_cmds", "cogs.ai_chat"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Successfully loaded {ext}")
            except Exception as e:
                print(f"CRITICAL: Failed to load {ext} -> {e}")

        # 3. Sync Slash Commands
        print("Syncing Slash Commands...")
        try:
            await self.tree.sync()
            print("--- SLASH COMMANDS SYNCED ---")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"SUCCESS: {self.user} is online and fully operational.")

    # --- THE GLOBAL ERROR HANDLER ---
    async def on_command_error(self, ctx: commands.Context, error):
        # 1. Ignore "Command not found" so the AI chat can handle normal conversation
        if isinstance(error, commands.CommandNotFound):
            return
            
        # 2. If the user forgets to tag someone or misses an argument
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("You forgot an argument. Use the command properly.", ephemeral=True)
            
        # 3. If the user tags a name that doesn't exist in the server
        elif isinstance(error, commands.MemberNotFound) or isinstance(error, commands.UserNotFound):
            return await ctx.send("I can't find that user. Make sure you are providing a valid ID or tag.", ephemeral=True)
            
        # 4. If a Hybrid command fails to parse the input
        elif isinstance(error, commands.HybridCommandError):
            return await ctx.send("I can't process that input. Double-check your formatting.", ephemeral=True)
            
        # 5. Log anything else to the console so we can debug it later
        else:
            print(f"Unhandled Command Error: {error}")

# 3. Startup Logic
if __name__ == "__main__":
    # Start the web server first so Render sees the open port immediately
    keep_alive()
    
    if TOKEN:
        bot = EsdeathBot()
        print("Initiating Discord Login...")
        bot.run(TOKEN)
    else:
        print("FATAL ERROR: dc_token missing from environment variables!")
        sys.exit(1)
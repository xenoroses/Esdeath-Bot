import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from flask import Flask
from threading import Thread
import asyncio

# Web Server for UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()
TOKEN = os.getenv("dc_token")

class EsdeathBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Zen")
        )
        self.redis = None

    async def setup_hook(self):
        print("--- Starting Setup Hook ---")
        
        # 1. Initialize Redis (Non-blocking with timeout)
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
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"Successfully loaded extension: {extension}")
            except Exception as e:
                print(f"CRITICAL: Failed to load extension {extension} -> {e}")

        # 3. Sync slash commands
        print("Syncing Slash Commands...")
        try:
            await self.tree.sync()
            print("Slash Commands synced.")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"CONNECTED: Logged in as {self.user}")
        print("--- Esdeath is fully operational ---")

bot = EsdeathBot()
keep_alive()

if TOKEN:
    print("Initiating Discord handshake...")
    bot.run(TOKEN)
else:
    print("ERROR: No Discord token found!")
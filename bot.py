import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from flask import Flask
from threading import Thread

# Web Server for UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive"

def run():
    # Render uses the PORT environment variable
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
        
        # Initialize Redis
        self.redis = Redis(
            url=os.getenv("UPSTASH_REDIS_REST_URL"),
            token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
        )

    async def setup_hook(self):
        print("--- Starting Setup Hook ---")
        
        # Load Cogs with error reporting
        extensions = ["cogs.staff_cmds", "cogs.ai_chat"]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"Successfully loaded extension: {extension}")
            except Exception as e:
                print(f"CRITICAL: Failed to load extension {extension} -> {e}")

        # Sync slash commands
        print("Syncing Slash Commands (this can take a moment)...")
        try:
            await self.tree.sync()
            print("Systems Online. Slash Commands synced successfully.")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"CONNECTED: Logged in as {self.user} (ID: {self.user.id})")
        print(f"Active in {len(self.guilds)} servers.")
        print("--- Esdeath is fully operational ---")

# Initialize and Run
bot = EsdeathBot()

# Start the keep_alive ping server
keep_alive()

# Start the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No Discord token found in Environment Variables!")
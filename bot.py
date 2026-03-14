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
        
        self.redis = Redis(
            url=os.getenv("UPSTASH_REDIS_REST_URL"),
            token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
        )

    async def setup_hook(self):
        # Load the separate files from the cogs folder
        await self.load_extension("cogs.staff_cmds")
        await self.load_extension("cogs.ai_chat")
        
        # Sync slash commands
        await self.tree.sync()
        print("Systems Online. Cogs loaded and Slash Commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user}")

bot = EsdeathBot()

keep_alive()
bot.run(TOKEN)
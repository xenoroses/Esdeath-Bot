import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from eval_bridge import register_bot, app as eval_app
from flask import Flask
from threading import Thread
import asyncio
import sys
import logging
import uvicorn
import certifi

# --- 1. GLOBAL ENVIRONMENT & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Permanent Architectural Fix: Fix SSL validation issues in containers globally
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())

logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒞ℒℰ𝒜𝒩 𝒜ℛ𝒞ℋ𝒐𝒯ℰ𝒞𝒯𝒰ℛℰ ℒ𝒪𝒜𝒟ℰ𝒟**")

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    return "Hyacine is alive and guarding Hugging Face."

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    # Suppress werkzeug logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port)

def start_eval_server():
    uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning")

def keep_alive():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    eval_thread = Thread(target=start_eval_server, daemon=True)
    eval_thread.start()

# --- 3. BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")
PROXY = os.getenv("proxy") # Standard, clean proxy injection

from cache_layer import HyacineCache

HYACINE_DEFAULT_PREFIXES = ["!", ","]

async def get_server_prefixes(bot, message):
    if not message.guild or not getattr(bot, 'cache', None):
        return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)
    
    try:
        cached_prefixes = await bot.cache.get(f"prefixes:{message.guild.id}")
        if cached_prefixes:
            custom_prefixes = json.loads(cached_prefixes)
            if isinstance(custom_prefixes, list) and custom_prefixes:
                expanded = []
                for p in custom_prefixes:
                    expanded.append(p)
                    if p.replace(" ", "").isalnum() and not p.endswith(" "):
                        expanded.append(p + " ")
                final_prefixes = sorted(list(set(expanded + HYACINE_DEFAULT_PREFIXES)), key=len, reverse=True)
                return commands.when_mentioned_or(*final_prefixes)(bot, message)
    except Exception as e:
        logging.error(f"Prefix Fetch Error: {e}")
    return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)

class HyacineBot(commands.AutoShardedBot):
    """Clean, unpatched Discord bot architecture."""
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            proxy=PROXY, # Native proxy support (no monkey-patching required)
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸ℴ𝒽ℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True,
            shard_count=None 
        )
        self.redis = None
        self.cache = None

    async def setup_hook(self):
        logging.info("Initializing setup_hook...")
        self.tree.on_error = self.on_tree_error
        register_bot(self)
        try:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                logging.info("Connecting to Upstash Redis...")
                self.redis = Redis(url=url, token=token)
                self.cache = HyacineCache(self.redis)
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                logging.info("Redis Connection: SUCCESS")
            else:
                logging.error("FATAL: Redis Configuration Missing. Aborting startup.")
                sys.exit(1)
        except Exception as e:
            logging.error(f"FATAL REDIS FAILURE: {e}. Aborting startup.")
            sys.exit(1)

        extensions = [
            "cogs.staff_cmds", "cogs.ai_chat", "cogs.impersonator", "cogs.fun_cmds",
            "cogs.admin_cmds", "cogs.sticky_cmds", "cogs.forcenick_cmds",
            "cogs.afk_cmds", "cogs.trust_cmds", "cogs.smartpurge_cmds", 
            "cogs.ai_utility_cmds", "cogs.help_cmds", "cogs.intelligence_engine",
            "cogs.infrastructure_engine", "cogs.observability_engine",
            "cogs.prestige_engine", "cogs.social_engine", "cogs.lore_engine",
            "cogs.synaptic_social", "cogs.schedule_engine", "cogs.workflow_engine"
        ]

        logging.info(f"Loading {len(extensions)} extensions...")
        for ext in extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                logging.error(f"Failed to load {ext}: {e}")
        
        try:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} slash commands.")
        except Exception as e:
            logging.error(f"Sync Error: {e}")

    async def on_ready(self):
        logging.info(f"SUCCESS: {self.user} is online and operational.")
        if not hasattr(self, "presence_task"):
            self.presence_task = self.loop.create_task(self.rotate_presence())

    async def rotate_presence(self):
        presets = [
            (discord.Status.online, discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸𝒽ℴℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹")),
            (discord.Status.idle, discord.Activity(type=discord.ActivityType.listening, name="❂ 𝒯𝒽ℯ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒮𝓎𝓂Ⓟ𝒽ℴ𝓃𝓎"))
        ]
        while True:
            for status, activity in presets:
                await self.change_presence(status=status, activity=activity)
                await asyncio.sleep(300)

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound): return
        logging.error(f"Command Error: {error}")

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logging.error(f"Tree Error: {error}")

# --- 4. STARTUP LOGIC ---
async def main():
    keep_alive()
    
    if not TOKEN:
        logging.error("FATAL: dc_token missing from environment.")
        sys.exit(1)

    # Clean retry loop without DNS monkeypatching
    max_retries = 5
    for attempt in range(max_retries):
        logging.info(f"Connection Attempt #{attempt + 1}...")
        
        bot = HyacineBot()
        try:
            async with bot:
                await bot.start(TOKEN)
            break
        except Exception as e:
            logging.error(f"Link Failure: {e}")
            if "429" in str(e) or "1015" in str(e):
                wait_time = 60 * (attempt + 1)
                logging.warning(f"Throttled. Reconnection in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(5)
                if attempt == max_retries - 1:
                    logging.error("FATAL: All connection attempts exhausted.")
                    sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

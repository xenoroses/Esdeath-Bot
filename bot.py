import socket
import requests
import random
import discord
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
import time
import uvicorn
import atexit
from cache_layer import HyacineCache

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- 1. THE DOH MASTER BYPASS (DNS OVER HTTPS) ---
# Hugging Face's DNS servers block Discord. This bypasses them completely
# by asking Google's API for the real IPs via a standard web request.
print("Fetching live Discord IPs via Google DNS-over-HTTPS...")
try:
    d_com = requests.get("https://dns.google/resolve?name=discord.com&type=A", timeout=5).json()
    d_gg = requests.get("https://dns.google/resolve?name=gateway.discord.gg&type=A", timeout=5).json()
    
    DISCORD_COM_IPS = [ans['data'] for ans in d_com.get('Answer', []) if ans['type'] == 1]
    DISCORD_GG_IPS = [ans['data'] for ans in d_gg.get('Answer', []) if ans['type'] == 1]
    print(f"Bypass Successful! Found IPs: {len(DISCORD_COM_IPS)} API, {len(DISCORD_GG_IPS)} Gateway")
except Exception as e:
    print(f"DoH Bypass Failed: {e}")
    DISCORD_COM_IPS, DISCORD_GG_IPS = [], []

if not DISCORD_COM_IPS or not DISCORD_GG_IPS:
    print("WARNING: Discord API IP fetch failed - bot may not connect properly")

original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    safe_host = host.decode('utf-8') if isinstance(host, bytes) else host
    
    # Secretly swap the blocked hostname for a freshly fetched live IP
    if safe_host == "discord.com" and DISCORD_COM_IPS:
        return original_getaddrinfo(random.choice(DISCORD_COM_IPS), port, family, type, proto, flags)
    elif safe_host == "gateway.discord.gg" and DISCORD_GG_IPS:
        return original_getaddrinfo(random.choice(DISCORD_GG_IPS), port, family, type, proto, flags)
        
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    return "Hyacine is alive and guarding Hugging Face."

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port)

def start_eval_server():
    uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning")

def keep_alive():
    print("Starting Web Server Thread...")

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    eval_thread = Thread(target=start_eval_server)
    eval_thread.daemon = True
    eval_thread.start()

# --- 3. BOT INITIALIZATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")

def decode_redis_data(data):
    return data.decode('utf-8') if isinstance(data, bytes) else data

async def get_server_prefixes(bot, message):
    default_prefixes = [","]
    if not message.guild or not getattr(bot, 'cache', None):
        return commands.when_mentioned_or(*default_prefixes)(bot, message)
    try:
        cached_prefixes = await bot.cache.get(f"prefixes:{message.guild.id}")
        if cached_prefixes:
            # cache layer already decodes the data
            custom_prefixes = json.loads(cached_prefixes)
            return commands.when_mentioned_or(*custom_prefixes)(bot, message)
    except Exception as e:
        print(f"Prefix Fetch Error: {e}")
    return commands.when_mentioned_or(*default_prefixes)(bot, message)

class HyacineBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸𝒽ℴℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True
        )
        self.last_result = None
        self.redis = None
        self.cache = None

    async def setup_hook(self):
        register_bot(self)
        logging.info("--- SETUP HOOK STARTING ---")
        try:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                self.cache = HyacineCache(self.redis)
                for attempt in range(3):
                    try:
                        await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                        logging.info("Redis Connected successfully.")
                        break
                    except Exception as e:
                        if attempt == 2:
                            logging.warning(f"REDIS WARNING: Connection failed after retries. Error: {e}")
                        else:
                            logging.info(f"Redis connection attempt {attempt+1} failed, retrying...")
                            await asyncio.sleep(1)
            else:
                logging.error("REDIS ERROR: Missing Environment Variables.")
        except Exception as e:
            logging.warning(f"REDIS WARNING: Connection failed. Error: {e}")


        extensions = [
            "cogs.staff_cmds",
            "cogs.ai_chat",
            "cogs.impersonator",
            "cogs.fun_cmds",
            "cogs.admin_cmds",
            "cogs.sticky_cmds",
            "cogs.forcenick_cmds",
            "cogs.automod_engine",
            "cogs.afk_cmds",
            "cogs.trust_cmds",
            "cogs.smartpurge_cmds",
            "cogs.security_cmds",
            "cogs.ai_utility_cmds",
            "cogs.workflow_cmds",
            "cogs.help_cmds",
            "cogs.intelligence_engine",
            "cogs.infrastructure_engine",
            "cogs.observability_engine",
            "cogs.prestige_engine",
            "cogs.social_engine",
            "cogs.lore_engine"
        ]

        for ext in extensions:
            if ext not in self.extensions:
                try:
                    await self.load_extension(ext)
                    logging.info(f"Successfully loaded {ext}")
                except Exception as e:
                    logging.error(f"CRITICAL: Failed to load {ext} -> {e}")

        try:
            synced = await self.tree.sync()
            self._app_cmd_cache = {c.name: c.id for c in synced}
            with open("command_cache.json", "w") as f:
                json.dump(self._app_cmd_cache, f, indent=4)
            logging.info(f"--- SLASH COMMANDS SYNCED ({len(synced)} commands) ---")
        except Exception as e:
            logging.error(f"Sync Error: {e}")

    async def on_ready(self):
        self.start_time = time.time()
        print(f"BOT INSTANCE PID: {os.getpid()}")
        logging.info(f"SUCCESS: {self.user} is online and operational on Hugging Face.")
        # Start presence rotation
        if not hasattr(self, "presence_task"):
            self.presence_task = self.loop.create_task(self.rotate_presence())

    async def on_message(self, message):
        await self.process_commands(message)

    async def rotate_presence(self):
        statuses = [
            discord.Activity(type=discord.ActivityType.watching, name="Stalking Zen"),
            discord.Activity(type=discord.ActivityType.listening, name="Your Commands"),
            discord.Activity(type=discord.ActivityType.playing, name="With Fire"),
            discord.Activity(type=discord.ActivityType.watching, name="The Server")
        ]
        while True:
            for status in statuses:
                await self.change_presence(activity=status)
                await asyncio.sleep(300)  # 5 minutes

    async def on_command_error(self, ctx: commands.Context, error):
        # Ignore slash-command errors (hybrid commands trigger both)
        if ctx.interaction is not None:
            return

        # Ignore unknown commands
        if isinstance(error, commands.CommandNotFound):
            return

        # Prevent duplicate handling
        if getattr(ctx, "_error_handled", False):
            return
        ctx._error_handled = True

        if isinstance(error, commands.MissingRequiredArgument):
            missing_param = error.param.name
            command_name = ctx.command.qualified_name
            prefix = ctx.clean_prefix

            base_str = f"{prefix}{command_name} "
            current_len = len(base_str)

            signature_parts = []
            target_start_idx = 0
            target_length = 0

            for name, param in ctx.command.clean_params.items():
                part = f"<{name}>" if param.required else f"[{name}]"
                if name == missing_param:
                    target_start_idx = current_len
                    target_length = len(part)
                signature_parts.append(part)
                current_len += len(part) + 1

            full_command_str = base_str + " ".join(signature_parts)
            carets = (" " * target_start_idx) + ("^" * target_length)

            return await ctx.send(
                f"```\n"
                f"{full_command_str}\n"
                f"{carets}\n"
                f"{missing_param} is a required argument that is missing.\n"
                f"```"
            )

        print(f"Unhandled Command Error: {error}")

import psutil

# --- 4. STARTUP LOGIC ---
if __name__ == "__main__":
    # Singleton lock to prevent multiple bot instances
    LOCK_FILE = "bot.lock"
    
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            
            # Check if previous process is still alive
            if psutil.pid_exists(old_pid):
                print(f"Another bot instance (PID {old_pid}) detected. Forcefully terminating...")
                try:
                    p = psutil.Process(old_pid)
                    p.terminate()
                    p.wait(timeout=3)
                    print("Previous instance terminated. Proceeding.")
                except Exception as e:
                    print(f"Could not terminate old instance: {e}. Exiting to prevent duplication.")
                    sys.exit(0)
            else:
                print("Detected stale lock file. Cleaning up...")
                os.remove(LOCK_FILE)
        except Exception:
            # If file is empty or corrupted, just clear it
            os.remove(LOCK_FILE)
    
    # Create lock file with current PID
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # Cleanup function for lock file
    def cleanup_lock():
        if os.path.exists(LOCK_FILE):
            try:
                # Only remove if it belongs to us
                with open(LOCK_FILE, "r") as f:
                    if f.read().strip() == str(os.getpid()):
                        os.remove(LOCK_FILE)
            except: pass
    
    atexit.register(cleanup_lock)
    
    keep_alive()
    if TOKEN:
        print("Initiating Discord Login...")
        bot = HyacineBot()
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"FATAL ERROR ON STARTUP: {e}")
            sys.exit(1)
    else:
        print("FATAL ERROR: dc_token missing!")
        sys.exit(1)

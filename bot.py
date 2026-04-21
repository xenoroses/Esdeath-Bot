import socket
import httpx
import random
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
import time
import uvicorn
import atexit
import psutil
from cache_layer import HyacineCache

import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

import aiohttp

import ssl

# --- 1. THE DEEP STELLAR PATCH (DOH HIJACK) ---
async def fetch_discord_ips():
    """
    Fetches real terminal IPs via multiple DoH providers.
    Critical for bypassing DNS blocks in restricted environments like Hugging Face.
    """
    logging.info("Initiating Stellar DoH Bypass Sequence...")
    com_ips, gg_ips = set(), set()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            responses = await asyncio.gather(
                client.get("https://dns.google/resolve?name=discord.com&type=A"),
                client.get("https://dns.google/resolve?name=gateway.discord.gg&type=A"),
                return_exceptions=True
            )
            for i, resp in enumerate(responses):
                if isinstance(resp, httpx.Response) and resp.status_code == 200:
                    data = resp.json()
                    ips = [ans['data'] for ans in data.get('Answer', []) if ans['type'] == 1]
                    if i == 0: com_ips.update(ips)
                    else: gg_ips.update(ips)
        except: pass
        if not com_ips or not gg_ips:
            try:
                headers = {"Accept": "application/dns-json"}
                responses = await asyncio.gather(
                    client.get("https://cloudflare-dns.com/dns-query?name=discord.com&type=A", headers=headers),
                    client.get("https://cloudflare-dns.com/dns-query?name=gateway.discord.gg&type=A", headers=headers),
                    return_exceptions=True
                )
                for i, resp in enumerate(responses):
                    if isinstance(resp, httpx.Response) and resp.status_code == 200:
                        data = resp.json()
                        ips = [ans['data'] for ans in data.get('Answer', []) if ans['type'] == 1]
                        if i == 0: com_ips.update(ips)
                        else: gg_ips.update(ips)
            except: pass
    final_com = list(com_ips)
    final_gg = list(gg_ips)
    if final_com: logging.info(f"Resolved discord.com -> {final_com}")
    if final_gg: logging.info(f"Resolved gateway.discord.gg -> {final_gg}")
    return final_com, final_gg

DISCORD_COM_IPS, DISCORD_GG_IPS = [], []

# --- MONKEYPATCH: AIOHTTP DEEP RESOLUTION ---
original_resolve_host = aiohttp.TCPConnector._resolve_host

async def patched_resolve_host(self, host, port, traces=None):
    h_lower = host.lower()
    if h_lower == "discord.com" and DISCORD_COM_IPS:
        return [{"hostname": host, "host": random.choice(DISCORD_COM_IPS), "port": port, "family": socket.AF_INET, "proto": 0, "flags": 0}]
    elif h_lower == "gateway.discord.gg" and DISCORD_GG_IPS:
        return [{"hostname": host, "host": random.choice(DISCORD_GG_IPS), "port": port, "family": socket.AF_INET, "proto": 0, "flags": 0}]
    return await original_resolve_host(self, host, port, traces)

aiohttp.TCPConnector._resolve_host = patched_resolve_host

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
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    eval_thread = Thread(target=start_eval_server)
    eval_thread.daemon = True
    eval_thread.start()

# --- 3. BOT INITIALIZATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")
PROXY = os.getenv("proxy")

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
    """Tier S Architecture: Automatically handles sharding and deep DNS resolution."""
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Stellar SSL Context with fallback
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except:
            ssl_context = True
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            proxy=PROXY,
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
                # Use a timeout for the ping to prevent indefinite hanging
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                logging.info("Redis Connection: SUCCESS")
            else:
                logging.error("FATAL: Redis Configuration Missing. Hyacine requires a synchronized master state to operate safely. Aborting startup.")
                sys.exit(1)
        except asyncio.TimeoutError:
            logging.error("FATAL: Redis Connection TIMEOUT. Ensure your Upstash instance is reachable. Aborting startup.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"FATAL REDIS FAILURE: {e}. All logic gates require active synchronization. Aborting startup.")
            sys.exit(1)

        extensions = [
            "cogs.staff_cmds", "cogs.ai_chat", "cogs.impersonator", "cogs.fun_cmds",
            "cogs.admin_cmds", "cogs.sticky_cmds", "cogs.forcenick_cmds",
            "cogs.afk_cmds", "cogs.trust_cmds",
            "cogs.smartpurge_cmds", "cogs.ai_utility_cmds",
            "cogs.help_cmds", "cogs.intelligence_engine",
            "cogs.infrastructure_engine", "cogs.observability_engine",
            "cogs.prestige_engine", "cogs.social_engine", "cogs.lore_engine",
            "cogs.synaptic_social", "cogs.schedule_engine",
            "cogs.workflow_engine"
        ]

        logging.info(f"Loading {len(extensions)} extensions...")
        for ext in extensions:
            try:
                logging.info(f" -> Loading {ext}...")
                await self.load_extension(ext)
            except Exception as e:
                logging.error(f"Failed to load {ext}: {e}")
        logging.info("All extensions loaded.")

        try:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} slash commands.")
        except Exception as e:
            logging.error(f"Sync Error: {e}")

    async def on_ready(self):
        self.start_time = time.time()
        logging.info(f"SUCCESS: {self.user} represents the Stellar Symphony (PID: {os.getpid()})")
        if not hasattr(self, "presence_task"):
            self.presence_task = self.loop.create_task(self.rotate_presence())

    async def on_message(self, message):
        await self.process_commands(message)

    async def rotate_presence(self):
        """Rotates stellar activities and statuses to keep the engine dynamic."""
        presets = [
            (discord.Status.online, discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸𝒽ℴℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹")),
            (discord.Status.idle, discord.Activity(type=discord.ActivityType.listening, name="❂ 𝒯𝒽ℯ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒮𝓎𝓂Ⓟ𝒽ℴ𝓃𝓎")),
            (discord.Status.dnd, discord.Activity(type=discord.ActivityType.competing, name="⌬ 𝒞𝒶𝓁𝒞𝓊𝓁𝒶𝓉𝒾𝓃ℊ 𝒯ℯ𝓃𝓈𝒾ℴ𝓃")),
            (discord.Status.online, discord.Activity(type=discord.ActivityType.watching, name="𖦹 𝒮ℯ𝒶 ℴ𝒻 𝒬𝓊𝒶𝓃𝓉𝒶 𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎")),
            (discord.Status.idle, discord.Activity(type=discord.ActivityType.playing, name="⟡ 𝒫𝒶𝓉𝒽 ℴ𝒻 𝓉𝒽ℯ 𝒯𝓇𝒶𝒾𝓁𝒷𝓁𝒶𝒷ℯ𝓇"))
        ]
        while True:
            for status, activity in presets:
                await self.change_presence(status=status, activity=activity)
                await asyncio.sleep(300)

    async def on_error(self, event, *args, **kwargs):
        import traceback
        logging.error(f"Stellar Event Error in {event}: {traceback.format_exc()}")

    async def on_command_error(self, ctx: commands.Context, error):
        # --- IDEMPOTENCY LOCK: Prevent double error responses across bot instances ---
        if self.redis and not ctx.interaction:
            lock_key = f"lock:err:{ctx.message.id}"
            if not await self.redis.set(lock_key, "1", nx=True, ex=2):
                logging.info(f"Signal Synchronized: Suppressed dual-response for message {ctx.message.id}.")
                return

        if ctx.interaction and not ctx.interaction.response.is_done():
            try: await ctx.defer(ephemeral=True)
            except: pass
        if isinstance(error, commands.CommandNotFound): return
        if getattr(ctx, "_error_handled", False): return
        ctx._error_handled = True

        header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
        footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            usage = f"Usage: {ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            return await ctx.send(f"{header}```fix\n𝒮𝓎𝓈𝓉ℯ𝓂 ℛℯ𝓆𝓊𝒾𝓈𝒾𝓉𝒾ℴ𝓃 ℱ𝒶𝒾𝓁𝓊𝓇ℯ\n{usage}\n``` {footer}")
        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            return await ctx.send(f"{header}```fix\n𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ\nMissing: {perms}\n``` {footer}")
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"{header}```fix\n𝒯ℋℛ𝒪𝒯𝒯ℒℐ𝒩𝒢\nRetry in {error.retry_after:.1f}s\n``` {footer}")
        
        if isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            forbidden = error.original
            if forbidden.code == 50013:
                msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: I lack required permissions in this sector (likely `Embed Links` or `Read Message History`)."
                return await ctx.send(f"{header}```fix\n{msg}\n``` {footer}")

        logging.error(f"Command Error: {error}")
        if not ctx.interaction:
            await ctx.send(f"{header}```fix\n𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇\n{error}\n``` {footer}")

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Dedicated error handler for the Slash Command Tree."""
        # --- IDEMPOTENCY LOCK: Prevent double error responses across bot instances ---
        if self.redis:
            lock_key = f"lock:err:tree:{interaction.id}"
            if not await self.redis.set(lock_key, "1", nx=True, ex=2):
                return
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⌬ ⟡ **𝒯ℋℛ𝒪𝒯ℯℒℒℐ𝒩𝒢:** `{error.retry_after:.1f}s` remaining."
        elif isinstance(error, app_commands.MissingPermissions):
            msg = f"⌬ ⟡ **𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟:** You lack the permissions required for this gateway."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒫ℛℐ𝒱ℐℒℰ𝒢ℰ ℱ𝒜𝐼𝐿𝒰ℛℰ:** I lack `{', '.join(error.missing_permissions)}`."
        else:
            msg = f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** `{error}`"
            logging.error(f"Tree Error: {error}")

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            logging.error(f"Failed to send tree error response: {e}")

# --- 4. STARTUP LOGIC ---
async def main():
    """Main asynchronous entry point for the Hyacine Protocol."""
    global DISCORD_COM_IPS, DISCORD_GG_IPS
    DISCORD_COM_IPS, DISCORD_GG_IPS = await fetch_discord_ips()

    # --- 1. Aggressive Singleton Enforcement ---
    # We hunt for any other Python processes running 'bot.py' on this machine to kill ghost instances.
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] != os.getpid() and any('bot.py' in str(arg) for arg in (proc.info['cmdline'] or [])):
                logging.info(f"❂ Singleton Alert: Terminating stellar ghost process (PID: {proc.info['pid']})...")
                proc.terminate()
        except: pass

    LOCK_FILE = "bot.lock"
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if psutil.pid_exists(old_pid):
                try: 
                    psutil.Process(old_pid).terminate()
                    time.sleep(1)
                except: pass
            os.remove(LOCK_FILE)
        except: 
            if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
    
    with open(LOCK_FILE, "w") as f: f.write(str(os.getpid()))
    def cleanup_lock():
        try:
            with open(LOCK_FILE, "r") as f:
                if f.read().strip() == str(os.getpid()): os.remove(LOCK_FILE)
        except: pass
    atexit.register(cleanup_lock)

    keep_alive()
    
    if not TOKEN:
        logging.error("FATAL: dc_token missing.")
        sys.exit(1)

    max_retries = 5
    for attempt in range(max_retries):
        logging.info(f"Stellar Connection Attempt #{attempt + 1}...")
        
        # Diagnostic: Try a raw TCP probe to a resolved IP
        if DISCORD_COM_IPS:
            target_ip = random.choice(DISCORD_COM_IPS)
            logging.info(f"Probing Logic Gate (TCP) at {target_ip}:443...")
            try:
                conn = asyncio.open_connection(target_ip, 443)
                reader, writer = await asyncio.wait_for(conn, timeout=3.0)
                writer.close()
                await writer.wait_closed()
                logging.info(f"✧ TCP Probe SUCCESS: {target_ip} is reachable.")
                
                # Now try a TLS probe via httpx to see if DPI is blocking the SNI
                logging.info(f"Probing Stellar Handshake (TLS) for discord.com...")
                async with httpx.AsyncClient(verify=False) as client:
                    # We use verify=False just to see if we can get ANY response (like a 403 or 200)
                    # to determine if the connection is dropped or rejected.
                    resp = await client.get(f"https://{target_ip}", headers={"Host": "discord.com"}, timeout=5.0)
                    logging.info(f"✧ TLS Probe SUCCESS: Status {resp.status_code}")
            except Exception as probe_err:
                logging.error(f"⌬ Handshake FAILED: {probe_err}. This suggests Deep Packet Inspection (DPI) or a TLS-level block by the host.")

        bot = HyacineBot()
        try:
            async with bot:
                await bot.start(TOKEN)
            break
        except Exception as e:
            import traceback
            logging.error(f"Stellar Link Failure: {e}")
            logging.debug(traceback.format_exc())
            
            if "429" in str(e) or "1015" in str(e):
                wait_time = 60 * (attempt + 1)
                logging.warning(f"Throttled. Reconnection in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                # If it's not a rate limit, wait a bit anyway before retrying
                await asyncio.sleep(5)
                if attempt == max_retries - 1:
                    logging.error("FATAL: All connection attempts exhausted. System hibernating.")
                    sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

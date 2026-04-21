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
import ssl
import aiohttp

# --- STELLAR SYSTEM INITIALIZATION ---
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ 𝒜𝒞𝒯ℐ𝒱ℰ: 𝒫ℰℛℳ𝒜𝒩ℰ𝒩𝒯 ℱℐ𝒳 ℒ𝒪𝒜𝒟ℰ𝒟**")

# --- 1. THE DEEP STELLAR PATCH (DOH HIJACK) ---
async def fetch_discord_ips():
    """Fetches real terminal IPs via multiple DoH providers."""
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

# --- MONKEYPATCH: STELLAR SOVEREIGNTY (SSL & DNS BYPASS) ---
original_resolve_host = aiohttp.TCPConnector._resolve_host

async def patched_resolve_host(self, host, port, traces=None):
    h_lower = host.lower()
    if h_lower in ["discord.com", "gateway.discord.gg", "cdn.discordapp.com"]:
        # THE FIX: Surgical SSL Bypass for Discord hosts on Hugging Face
        self._ssl = False 
        ips = DISCORD_COM_IPS if h_lower == "discord.com" else DISCORD_GG_IPS
        if not ips: ips = DISCORD_COM_IPS # Fallback for CDN
        if ips:
            return [{"hostname": host, "host": random.choice(ips), "port": port, "family": socket.AF_INET, "proto": 0, "flags": 0}]
    return await original_resolve_host(self, host, port, traces)

aiohttp.TCPConnector._resolve_host = patched_resolve_host

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home():
    return "Hyacine is alive and guarding Hugging Face."

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)

def start_eval_server():
    uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning")

def keep_alive():
    Thread(target=run_flask, daemon=True).start()
    Thread(target=start_eval_server, daemon=True).start()

# --- 3. BOT INITIALIZATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")
PROXY = os.getenv("proxy")

async def get_server_prefixes(bot, message):
    if not message.guild or not getattr(bot, 'cache', None):
        return commands.when_mentioned_or("!", ",")(bot, message)
    try:
        cached = await bot.cache.get(f"prefixes:{message.guild.id}")
        if cached:
            prefixes = json.loads(cached)
            if prefixes:
                expanded = []
                for p in prefixes:
                    expanded.append(p)
                    if p.isalnum() and not p.endswith(" "): expanded.append(p + " ")
                return commands.when_mentioned_or(*sorted(list(set(expanded + ["!", ","])), key=len, reverse=True))(bot, message)
    except: pass
    return commands.when_mentioned_or("!", ",")(bot, message)

class HyacineBot(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            proxy=PROXY,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸ℴ𝒽ℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True
        )
        self.redis = None
        self.cache = None

    async def setup_hook(self):
        logging.info("Initializing setup_hook...")
        register_bot(self)
        try:
            url, token = os.getenv("UPSTASH_REDIS_REST_URL"), os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                self.cache = HyacineCache(self.redis)
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                logging.info("Redis Connection: SUCCESS")
            else:
                logging.error("FATAL: Redis Missing.")
                sys.exit(1)
        except Exception as e:
            logging.error(f"FATAL REDIS: {e}")
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
        for ext in extensions:
            try: await self.load_extension(ext)
            except Exception as e: logging.error(f"Failed {ext}: {e}")
        try: await self.tree.sync()
        except: pass

    async def on_ready(self):
        logging.info(f"SUCCESS: {self.user} is online.")
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

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound): return
        logging.error(f"Command Error: {error}")

# --- 4. STARTUP ---
async def main():
    global DISCORD_COM_IPS, DISCORD_GG_IPS
    DISCORD_COM_IPS, DISCORD_GG_IPS = await fetch_discord_ips()

    # Singleton Enforcement
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['pid'] != os.getpid() and any('bot.py' in str(arg) for arg in (proc.info['cmdline'] or [])):
                proc.terminate()
        except: pass

    keep_alive()
    if not TOKEN: sys.exit(1)

    max_retries = 5
    for attempt in range(max_retries):
        logging.info(f"Stellar Connection Attempt #{attempt + 1}...")
        
        # Probe
        if DISCORD_COM_IPS:
            target = random.choice(DISCORD_COM_IPS)
            try:
                # Raw TCP Probe
                _, writer = await asyncio.wait_for(asyncio.open_connection(target, 443), timeout=3.0)
                writer.close()
                await writer.wait_closed()
                logging.info(f"✧ TCP SUCCESS: {target}")
                
                # TLS Probe (verify=False mirrors the fix)
                async with httpx.AsyncClient(verify=False) as client:
                    resp = await client.get(f"https://{target}", headers={"Host": "discord.com"}, timeout=5.0)
                    logging.info(f"✧ TLS SUCCESS: {resp.status_code}")
            except Exception as e:
                logging.error(f"⌬ PROBE FAILED: {e}")

        bot = HyacineBot()
        try:
            async with bot:
                await bot.start(TOKEN)
            break
        except Exception as e:
            logging.error(f"Stellar Link Failure: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

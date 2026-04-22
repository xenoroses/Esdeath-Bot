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
import ssl
import aiohttp
import httpx
import random
import socket

# --- 1. THE SOVEREIGN RESOLVER (PERMANENT DOH BYPASS) ---
class SovereignResolver(aiohttp.abc.AbstractResolver):
    """
    A professional DNS-over-HTTPS resolver that bypasses host DNS blocks.
    Self-contained, permanent, and doesn't rely on system configuration.
    """
    def __init__(self):
        self.cache = {}
        self.doh_urls = [
            "https://dns.google/resolve?name={host}&type=A",
            "https://cloudflare-dns.com/dns-query?name={host}&type=A"
        ]

    async def resolve(self, host, port=0, family=socket.AF_INET):
        if family != socket.AF_INET:
            # Force IPv4 to bypass broken HF IPv6 routing
            family = socket.AF_INET
            
        h_lower = host.lower()
        if h_lower in ["discord.com", "gateway.discord.gg", "cdn.discordapp.com"]:
            if h_lower in self.cache and time.time() < self.cache[h_lower]['expiry']:
                return self.cache[h_lower]['ips']

            logging.info(f"Sovereign Resolution: {host}")
            async with httpx.AsyncClient(timeout=5.0) as client:
                for url_template in self.doh_urls:
                    try:
                        headers = {"Accept": "application/dns-json"} if "cloudflare" in url_template else {}
                        resp = await client.get(url_template.format(host=host), headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            ips = [ans['data'] for ans in data.get('Answer', []) if ans['type'] == 1]
                            if ips:
                                result = [{"hostname": host, "host": ip, "port": port, "family": family, "proto": 0, "flags": 0} for ip in ips]
                                self.cache[h_lower] = {'ips': result, 'expiry': time.time() + 3600}
                                return result
                    except: continue
        
        # Fallback to standard resolution for non-Discord hosts
        return await aiohttp.ThreadedResolver().resolve(host, port, family)

    async def close(self):
        pass

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒩ℰ𝒯𝒲𝒪ℛ𝒦 𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩𝒯𝒴 𝒜𝒞𝒯ℐ𝒱ℰ**")

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home(): return "Hyacine is alive and guarding Hugging Face."

def keep_alive():
    port = int(os.environ.get("PORT", 7860))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    Thread(target=lambda: uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning"), daemon=True).start()

# --- 3. BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")

from cache_layer import HyacineCache
HYACINE_DEFAULT_PREFIXES = ["!", ","]

async def get_server_prefixes(bot, message):
    if not message.guild or not getattr(bot, 'cache', None):
        return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)
    try:
        cached = await bot.cache.get(f"prefixes:{message.guild.id}")
        if cached:
            prefixes = json.loads(cached)
            if isinstance(prefixes, list) and prefixes:
                expanded = []
                for p in prefixes:
                    expanded.append(p); 
                    if p.replace(" ", "").isalnum() and not p.endswith(" "): expanded.append(p + " ")
                return commands.when_mentioned_or(*sorted(list(set(expanded + HYACINE_DEFAULT_PREFIXES)), key=len, reverse=True))(bot, message)
    except: pass
    return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)

class HyacineBot(commands.AutoShardedBot):
    def __init__(self):
        # Sovereign SSL Context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Sovereign Connector: Custom Resolver + Forced IPv4 + Bundled SSL
        connector = aiohttp.TCPConnector(
            resolver=SovereignResolver(),
            family=socket.AF_INET,
            ssl=ssl_context
        )
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            connector=connector,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸ℴ𝒽ℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True
        )
        self.redis, self.cache = None, None

    async def setup_hook(self):
        register_bot(self)
        try:
            url, token = os.getenv("UPSTASH_REDIS_REST_URL"), os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                self.cache = HyacineCache(self.redis)
                await self.redis.ping()
        except: sys.exit(1)

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
        logging.info(f"SUCCESS: {self.user} is online via Sovereign Path.")

# --- 4. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    for attempt in range(5):
        logging.info(f"Ghost Protocol Handshake Attempt #{attempt + 1}...")
        
        # 1. Identity Spoofing: Mimic a real Chrome browser to bypass "Bot-Only" firewalls
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }

        # 2. Sovereign SSL: Force certifi but allow fallbacks
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE # Final connectivity priority
        
        # 3. Ghost Connector: Custom Resolver + Forced IPv4 + Browser Spoof
        connector = aiohttp.TCPConnector(
            resolver=SovereignResolver(),
            family=socket.AF_INET,
            ssl=ssl_ctx
        )
        
        bot = HyacineBot()
        bot.http.user_agent = browser_headers["User-Agent"]
        bot.http.connector = connector
        
        try:
            async with bot: await bot.start(TOKEN)
            break
        except Exception as e:
            err_str = str(e)
            if "Cannot connect" in err_str or "ssl" in err_str:
                logging.warning(f"Ghost Protocol Deflected: {err_str}. Re-calibrating...")
            else:
                logging.error(f"Link Failure: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

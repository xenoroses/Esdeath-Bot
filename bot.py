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
import aiohttp
import random

# --- 1. GLOBAL SSL FIX ---
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒜𝒰𝒯𝒪𝒩𝒪ℳ𝒪𝒰𝒮 ℛℰℒ𝒜𝒴 ℰ𝒩𝒢ℐ𝒩ℰ**")

# --- 2. AUTONOMOUS RELAY HARVESTER (ZERO-CONFIG PERMA-FIX) ---
# Since Hugging Face drops all packets to Discord, we MUST use a proxy.
# This engine automatically scrapes, tests, and uses free public proxies.
async def get_working_proxy():
    logging.info("⌬ ⟡ Initiating Autonomous Relay Harvest...")
    PROXY_URLS = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    proxies = []
    
    # 1. Scrape latest free proxies
    async with aiohttp.ClientSession() as session:
        for url in PROXY_URLS:
            try:
                async with session.get(url, timeout=5) as resp:
                    text = await resp.text()
                    proxies.extend([f"http://{line.strip()}" for line in text.split('\n') if line.strip()])
            except Exception as e:
                pass
                
    proxies = list(set(proxies))
    random.shuffle(proxies)
    logging.info(f"⌬ ⟡ Harvested {len(proxies)} candidate relays. Testing for resonance...")

    # 2. Lightning-fast concurrency tester
    async def test_proxy(proxy):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as test_session:
                async with test_session.get("https://discord.com", proxy=proxy, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status in [200, 301, 302, 403, 404]:
                        return proxy
        except: pass
        return None

    # 3. Test in chunks and return the absolute fastest one
    for i in range(0, min(1000, len(proxies)), 100):
        chunk = proxies[i:i+100]
        tasks = [asyncio.create_task(test_proxy(p)) for p in chunk]
        
        for coro in asyncio.as_completed(tasks):
            res = await coro
            if res:
                for t in tasks: t.cancel()
                logging.info(f"✧ Optimal Relay Established: {res}")
                return res
    return None

# --- 3. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home(): return "Hyacine is alive and guarding Hugging Face."

def keep_alive():
    port = int(os.environ.get("PORT", 7860))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    Thread(target=lambda: uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning"), daemon=True).start()

# --- 4. BOT CONFIGURATION ---
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
    def __init__(self, relay_url):
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            proxy=relay_url, # Inject the harvested proxy
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
        logging.info(f"SUCCESS: {self.user} is online via Autonomous Relay.")

# --- 5. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    # Indefinite self-healing loop
    for attempt in range(100):
        proxy_url = await get_working_proxy()
        if not proxy_url:
            logging.error("No valid relays found. Recalibrating in 15 seconds...")
            await asyncio.sleep(15)
            continue
            
        logging.info(f"Relay Handshake Attempt #{attempt + 1} using {proxy_url}...")
        bot = HyacineBot(proxy_url)
        
        try:
            async with bot: await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Link Failure: {e}")
            await asyncio.sleep(5) # Fast retry to grab a new proxy

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

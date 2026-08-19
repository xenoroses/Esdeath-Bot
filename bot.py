import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
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
from redis_utils import rget_json

# --- 1. GLOBAL SSL FIX ---
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒱𝒜𝒩𝒢𝒰𝒜ℛ𝒟 ℰ𝒩𝒢ℐ𝒩ℰ v3.1**")

# --- 2. THE DOH MASTER BYPASS (DNS OVER HTTPS) ---
async def fetch_discord_ips():
    """Fetches real terminal IPs via Google's DNS-over-HTTPS API."""
    logging.info("⌬ ⟡ Initiating DoH Bypass Protocol...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://dns.google/resolve?name=discord.com&type=A", timeout=5.0) as r1:
                d_com = await r1.json()
            async with session.get("https://dns.google/resolve?name=gateway.discord.gg&type=A", timeout=5.0) as r2:
                d_gg = await r2.json()
            
            com_ips = [ans['data'] for ans in d_com.get('Answer', []) if ans['type'] == 1]
            gg_ips = [ans['data'] for ans in d_gg.get('Answer', []) if ans['type'] == 1]
            logging.info(f"⌬ ⟡ Bypass Successful! Found IPs: {len(com_ips)} API, {len(gg_ips)} Gateway")
            return com_ips, gg_ips
        except Exception as e:
            logging.error(f"DoH Bypass Error: {e}")
            return [], []

import socket
DISCORD_COM_IPS, DISCORD_GG_IPS = [], []
original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    safe_host = host.decode('utf-8') if isinstance(host, bytes) else host
    if safe_host == "discord.com" and DISCORD_COM_IPS:
        return original_getaddrinfo(random.choice(DISCORD_COM_IPS), port, family, type, proto, flags)
    elif safe_host == "gateway.discord.gg" and DISCORD_GG_IPS:
        return original_getaddrinfo(random.choice(DISCORD_GG_IPS), port, family, type, proto, flags)
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo

# --- 3. ADVANCED AUTONOMOUS RELAY HARVESTER (FALLBACK) ---
async def get_working_proxy():
    logging.info("⌬ ⟡ Initiating Advanced Relay Harvest...")
    url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
    proxies = []
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                text = await resp.text()
                proxies = [f"http://{line.strip()}" for line in text.split('\n') if line.strip()]
        except Exception as e:
            logging.error(f"Harvest Failure: {e}")
            
    if not proxies:
        return None

    random.shuffle(proxies)
    logging.info(f"⌬ ⟡ Harvested {len(proxies)} candidate relays. Testing for resonance...")

    async def test_proxy(proxy):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as test_session:
                async with test_session.get("https://discord.com", proxy=proxy, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in [200, 301, 302, 403, 404]:
                        return proxy
        except: pass
        return None

    for i in range(0, min(500, len(proxies)), 50):
        chunk = proxies[i:i+50]
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
    if os.environ.get("SPACE_ID") or os.environ.get("SPACE_HOST") or os.environ.get("GRADIO_SERVER_PORT"):
        logging.info("⌬ ⟡ Hugging Face Space detected. Gradio managing port 7860.")
        return
    try:
        port = int(os.environ.get("PORT", 7860))
        logging.info(f"⌬ ⟡ Initiating Keep-Alive Heartbeat on port {port}...")
        Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
        Thread(target=lambda: uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning"), daemon=True).start()
    except Exception as e:
        logging.info(f"Keep-alive webserver notice: {e}")

# --- 4. BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("dc_token") or os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")

HYACINE_DEFAULT_PREFIXES = ["!", ","]

async def get_server_prefixes(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)
    try:
        prefixes = await rget_json(bot, f"prefixes:{message.guild.id}")
        if isinstance(prefixes, list) and prefixes:
            expanded = []
            for p in prefixes:
                expanded.append(p)
                if p.replace(" ", "").isalnum() and not p.endswith(" "): expanded.append(p + " ")
            return commands.when_mentioned_or(*sorted(list(set(expanded + HYACINE_DEFAULT_PREFIXES)), key=len, reverse=True))(bot, message)
    except: pass
    return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)

class HyacineBot(commands.AutoShardedBot):
    def __init__(self, relay_url):
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            proxy=relay_url, 
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸ℴ𝒽ℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        register_bot(self)

        extensions = [
            "cogs.staff_cmds", "cogs.impersonator", "cogs.fun_cmds",
            "cogs.admin_cmds", "cogs.sticky_cmds", "cogs.forcenick_cmds",
            "cogs.afk_cmds", "cogs.help_cmds",
            "cogs.infrastructure_engine", "cogs.observability_engine",
            "cogs.autodelete_engine"
        ]
        for ext in extensions:
            try: await self.load_extension(ext)
            except Exception as e: logging.error(f"Failed {ext}: {e}")
        try: await self.tree.sync()
        except: pass

    async def on_ready(self):
        logging.info(f"SUCCESS: {self.user} is online via Autonomous Relay.")
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logging.info(f"Purged guild command overrides for {guild.name} ({guild.id}) - 0 duplicates.")
            except Exception as e:
                logging.warning(f"Could not purge guild tree for {guild.id}: {e}")

# --- 5. STARTUP ---
async def main():
    global DISCORD_COM_IPS, DISCORD_GG_IPS

    keep_alive()
    if not TOKEN:
        logging.error("❌ CRITICAL: No Discord Bot Token found! Please set Secret 'dc_token' or 'DISCORD_TOKEN' in Hugging Face Space Settings.")
        return

    DISCORD_COM_IPS, DISCORD_GG_IPS = await fetch_discord_ips()
    
    attempts = 10
    for attempt in range(attempts):
        use_proxy = (attempt >= 2)
        proxy_url = None
        
        if use_proxy:
            logging.warning(f"Direct link unstable. Attempting Relay Harvest (Attempt #{attempt+1})...")
            proxy_url = await get_working_proxy()
            if not proxy_url:
                await asyncio.sleep(5)
                continue
        else:
            logging.info(f"Link Handshake Attempt #{attempt + 1} (Direct Connection)...")

        bot = HyacineBot(proxy_url)
        try:
            async with bot: await bot.start(TOKEN)
            break
        except Exception as e:
            logging.error(f"Link Failure: {e}")
            await asyncio.sleep(5) 

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

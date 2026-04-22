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

# --- 1. GLOBAL SSL FIX ---
# This ensures that even when passing through the proxy, the SSL handshake is verified correctly
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: ℒ𝒪𝒪𝒫ℬ𝒜𝒞𝒦 𝒯𝒰𝒩𝒩ℰℒ 𝒜𝒞𝒯ℐ𝒱ℰ**")

# --- 2. INTERNAL LOOPBACK TUNNEL (ZERO-CONFIG BYPASS) ---
# Hugging Face blocks Discord's IPs at the DNS/aiohttp level.
# This creates a genuine HTTP CONNECT proxy that bypasses it.
DNS_CACHE = {
    'discord.com': '162.159.138.232',
    'gateway.discord.gg': '162.159.136.234',
    'cdn.discordapp.com': '162.159.133.233'
}

async def handle_client(reader, writer):
    request_line = await reader.readline()
    if not request_line:
        writer.close()
        return
    
    try:
        method, url, version = request_line.decode().strip().split(' ')
    except:
        writer.close()
        return

    if method == 'CONNECT':
        host, port = url.split(':')
        port = int(port)
        
        # Drain headers
        while True:
            line = await reader.readline()
            if line == b'\r\n': break
                
        ip = DNS_CACHE.get(host, host)
        
        try:
            remote_reader, remote_writer = await asyncio.open_connection(ip, port)
            writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            await writer.drain()
            
            async def forward(r, w):
                try:
                    while True:
                        data = await r.read(8192)
                        if not data: break
                        w.write(data)
                        await w.drain()
                except: pass
                try: w.close()
                except: pass

            asyncio.create_task(forward(reader, remote_writer))
            asyncio.create_task(forward(remote_reader, writer))
        except Exception as e:
            writer.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
            await writer.drain()
            writer.close()
    else:
        writer.close()

def run_tunnel():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = loop.run_until_complete(asyncio.start_server(handle_client, '127.0.0.1', 8888))
    loop.run_until_complete(server.serve_forever())

# --- 3. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home(): return "Hyacine is alive and guarding Hugging Face."

def keep_alive():
    port = int(os.environ.get("PORT", 7860))
    Thread(target=run_tunnel, daemon=True).start()
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
    def __init__(self):
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            proxy="http://127.0.0.1:8888", # Direct traffic through our Loopback Tunnel
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
        logging.info(f"SUCCESS: {self.user} is online via Loopback Tunnel.")

# --- 5. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    # Small delay to ensure the Loopback Tunnel thread is listening
    await asyncio.sleep(2)

    for attempt in range(5):
        logging.info(f"Tunnel Handshake Attempt #{attempt + 1}...")
        bot = HyacineBot()
        try:
            async with bot: await bot.start(TOKEN)
            break
        except Exception as e:
            logging.error(f"Link Failure: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

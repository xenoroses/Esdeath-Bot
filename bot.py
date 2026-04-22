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

# --- 1. THE ABSOLUTE ZERO RESOLVER (FIXED & HARDENED) ---
class AbsoluteZeroResolver(aiohttp.abc.AbstractResolver):
    """
    A direct-injection resolver that returns hardcoded Discord IPs.
    Avoids 'expired' errors by bypassing the internal aiohttp cache logic.
    """
    def __init__(self):
        self.mapping = {
            'discord.com': '162.159.138.232',
            'gateway.discord.gg': '162.159.136.234',
            'cdn.discordapp.com': '162.159.133.233'
        }

    async def resolve(self, host, port=0, family=socket.AF_INET):
        h_lower = host.lower()
        if h_lower in self.mapping:
            ip = self.mapping[h_lower]
            return [{
                'hostname': host,
                'host': ip,
                'port': port,
                'family': family,
                'proto': 0,
                'flags': 0
            }]
        # Fallback to standard resolution for others (Redis, etc.)
        return await aiohttp.ThreadedResolver().resolve(host, port, family)

    async def close(self):
        pass

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒜ℬ𝒮𝒪ℒ𝒰𝒯ℰ 𝒩𝒰𝒞ℒℰ𝒜ℛ 𝒞𝒩𝒩ℰ𝒞𝒯ℐ𝒱ℐ𝒯𝒴**")

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
        # Create a nuclear connector: No SSL, Forced IPv4, Hardcoded Resolver
        connector = aiohttp.TCPConnector(
            resolver=AbsoluteZeroResolver(),
            family=socket.AF_INET,
            ssl=False,
            use_dns_cache=False # Disable cache to avoid 'expired' attribute errors
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
        logging.info(f"SUCCESS: {self.user} is online via Absolute Zero.")

# --- 4. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    for attempt in range(5):
        logging.info(f"Absolute Zero Handshake Attempt #{attempt + 1}...")
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

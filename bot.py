import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from eval_bridge import register_bot, app as eval_app
from flask import Flask, request, Response
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

# --- 1. THE INTERNAL LOOPBACK BRIDGE (ZERO-CONFIG BYPASS) ---
# This starts a local proxy on 127.0.0.1 that uses httpx to reach Discord.
# httpx is not blocked by HF, so it acts as our internal "tunnel".

bridge_app = Flask(__name__)

@bridge_app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    url = f"https://discord.com/{path}"
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    try:
        with httpx.Client(verify=False, timeout=10.0) as client:
            resp = client.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.get_data(),
                params=request.args
            )
            return Response(resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        return str(e), 502

def run_bridge():
    # Run the bridge on a high local port
    uvicorn.run(bridge_app, host="127.0.0.1", port=8888, log_level="error")

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: ℒ𝒪𝒪𝒫ℬ𝒜𝒞𝒦 ℬℛℐ𝒟𝒢ℰ 𝒜𝒞𝒯ℐ𝒱ℰ**")

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home(): return "Hyacine is alive and guarding Hugging Face."

def keep_alive():
    port = int(os.environ.get("PORT", 7860))
    Thread(target=run_bridge, daemon=True).start()
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
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            # Point the bot to our internal loopback bridge
            proxy="http://127.0.0.1:8888",
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
        logging.info(f"SUCCESS: {self.user} is online via Loopback Bridge.")

# --- 4. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    for attempt in range(5):
        logging.info(f"Loopback Handshake Attempt #{attempt + 1}...")
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

import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from upstash_redis.asyncio import Redis
from flask import Flask
from threading import Thread
import asyncio
import sys

# --- 1. WEB SERVER SETUP (For Hugging Face Keep-Alive) ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    return "Esdeath is alive and guarding Hugging Face."

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    # Run silently to prevent console spam
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    print("Starting Web Server Thread...")
    t = Thread(target=run_flask)
    t.daemon = True 
    t.start()

# --- 2. BOT INITIALIZATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")

async def get_server_prefixes(bot, message):
    default_prefixes = ["!", "esdeath ", "es "]
    if not message.guild or not getattr(bot, 'redis', None):
        return commands.when_mentioned_or(*default_prefixes)(bot, message)
    try:
        cached_prefixes = await bot.redis.get(f"prefixes:{message.guild.id}")
        if cached_prefixes:
            # Safely decode if Redis returns bytes
            if isinstance(cached_prefixes, bytes):
                cached_prefixes = cached_prefixes.decode('utf-8')
            custom_prefixes = json.loads(cached_prefixes)
            return commands.when_mentioned_or(*custom_prefixes)(bot, message)
    except Exception as e:
        print(f"Prefix Fetch Error: {e}")
    return commands.when_mentioned_or(*default_prefixes)(bot, message)

class EsdeathBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=intents,
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Stalking Zen"),
            help_command=None
        )
        self.redis = None

    async def setup_hook(self):
        print("--- SETUP HOOK STARTING ---")
        try:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                await asyncio.wait_for(self.redis.ping(), timeout=5.0)
                print("Redis Connected successfully.")
            else:
                print("REDIS ERROR: Missing Environment Variables.")
        except Exception as e:
            print(f"REDIS WARNING: Connection failed. Error: {e}")

        extensions = ["cogs.staff_cmds", "cogs.ai_chat", "cogs.impersonator"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Successfully loaded {ext}")
            except Exception as e:
                print(f"CRITICAL: Failed to load {ext} -> {e}")

        try:
            await self.tree.sync()
            print("--- SLASH COMMANDS SYNCED ---")
        except Exception as e:
            print(f"Sync Error: {e}")

    async def on_ready(self):
        print(f"SUCCESS: {self.user} is online and operational on Hugging Face.")

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            missing_param = error.param.name
            command_name = ctx.command.qualified_name
            prefix = ctx.clean_prefix
            
            # Base string (e.g., "es warn ")
            base_str = f"{prefix}{command_name} "
            current_len = len(base_str)
            
            signature_parts = []
            target_start_idx = 0
            target_length = 0
            
            # Reconstruct the signature and find the missing param's position
            for name, param in ctx.command.clean_params.items():
                part = f"<{name}>" if param.required else f"[{name}]"
                    
                if name == missing_param:
                    target_start_idx = current_len
                    target_length = len(part)
                    
                signature_parts.append(part)
                current_len += len(part) + 1 
                
            full_command_str = base_str + " ".join(signature_parts)
            
            # Draw the spaces and the carets
            carets = (" " * target_start_idx) + ("^" * target_length)
            
            # Send the Carl-bot formatted codeblock
            error_msg = f"```\n{full_command_str}\n{carets}\n{missing_param} is a required argument that is missing.\n```"
            await ctx.send(error_msg)
            
        else:
            print(f"Unhandled Command Error: {error}")

# --- 3. STARTUP LOGIC ---
if __name__ == "__main__":
    keep_alive()
    
    if TOKEN:
        print("Initiating Discord Login...")
        bot = EsdeathBot()
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"FATAL ERROR ON STARTUP: {e}")
            sys.exit(1)
    else:
        print("FATAL ERROR: dc_token missing!")
        sys.exit(1)
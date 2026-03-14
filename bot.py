import discord
import os
import random
import asyncio
import json
import time
from dotenv import load_dotenv
from llm import generate_reply
from upstash_redis.asyncio import Redis

from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Esdeath is alive"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()

TOKEN = os.getenv("dc_token")

# Initialize Upstash Redis for Persistent Memory
redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(
    intents=intents,
    status=discord.Status.idle,
    activity=discord.Activity(type=discord.ActivityType.watching, name="Zen")
)

MAX_HISTORY = 12

# Rate Limiting Trackers
COOLDOWN_TIME = 8 # Seconds users have to wait between bot pings
channel_cooldowns = {}
channel_warnings = {}

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    mentioned = client.user in message.mentions
    name_called = content.startswith("esdeath")
    random_reply = random.random() < 0.03

    if not (mentioned or name_called or random_reply):
        return

    channel_id = str(message.channel.id)
    current_time = time.time()

    # --- RATE LIMITER & SASSY WARNINGS ---
    last_msg_time = channel_cooldowns.get(channel_id, 0)
    if current_time - last_msg_time < COOLDOWN_TIME:
        # If they are spamming, check if we already warned them recently
        last_warn_time = channel_warnings.get(channel_id, 0)
        if current_time - last_warn_time > COOLDOWN_TIME:
            warnings = [
                "god, you're needy. give me a second.",
                "stop spamming me, i'm reading.",
                "take a breath, try-hard. i'll reply when i want to.",
                "do you ever shut up? wait a sec."
            ]
            await message.reply(random.choice(warnings), mention_author=False)
            channel_warnings[channel_id] = current_time
        return # Drop the message so it doesn't go to the LLM

    # Update the cooldown timer since we are about to process a valid message
    channel_cooldowns[channel_id] = current_time


    # --- PULL MEMORY FROM THE CLOUD ---
    try:
        history_data = await redis.get(f"memory:{channel_id}")
        if history_data:
            if isinstance(history_data, str):
                channel_memory = json.loads(history_data)
            else:
                channel_memory = history_data
        else:
            channel_memory = []
    except Exception as e:
        print("Redis get error:", e)
        channel_memory = []


    # --- TOKEN SAVER: TRUNCATE LONG MESSAGES ---
    safe_content = message.content
    if len(safe_content) > 300:
        safe_content = safe_content[:300] + "... [message too long, ignoring the rest]"


    # --- FORMAT THE MESSAGE ---
    if message.author.id == 456811056090578975:
        user_message = f"User Zen (ID:{message.author.id}): {safe_content}"
    else:
        user_message = f"User (ID:{message.author.id}): {safe_content}"

    channel_memory.append({
        "role": "user",
        "content": user_message
    })

    channel_memory = channel_memory[-MAX_HISTORY:]

    try:
        async with message.channel.typing():
            # Pass the memory array to the LLM
            reply = await asyncio.to_thread(
                generate_reply,
                channel_memory
            )

        await message.reply(reply, mention_author=False)

        channel_memory.append({
            "role": "assistant",
            "content": reply
        })
        
        # --- SAVE MEMORY BACK TO THE CLOUD ---
        try:
            await redis.set(f"memory:{channel_id}", json.dumps(channel_memory))
        except Exception as e:
            print("Redis set error:", e)

    except Exception as e:
        print("LLM Error:", e)
        await message.reply("ugh something broke for a second, try again", mention_author=False)

keep_alive()
client.run(TOKEN)
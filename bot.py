import discord
import os
import random
import asyncio
import json
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

client = discord.Client(intents=intents)

MAX_HISTORY = 12

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

    # 1. PULL MEMORY FROM THE CLOUD
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

    # 2. FORMAT THE MESSAGE
    if message.author.id == 456811056090578975:
        user_message = f"User Zen (ID:{message.author.id}): {message.content}"
    else:
        user_message = f"User (ID:{message.author.id}): {message.content}"

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
        
        # 3. SAVE MEMORY BACK TO THE CLOUD
        try:
            await redis.set(f"memory:{channel_id}", json.dumps(channel_memory))
        except Exception as e:
            print("Redis set error:", e)

    except Exception as e:
        print("LLM Error:", e)
        await message.reply("ugh something broke for a second, try again", mention_author=False)

keep_alive()
client.run(TOKEN)
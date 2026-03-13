import discord
import os
import random
import asyncio
from dotenv import load_dotenv
from llm import generate_reply

load_dotenv()

TOKEN = os.getenv("dc_token")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

channel_memory = {}

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

    channel_id = message.channel.id

    if channel_id not in channel_memory:
        channel_memory[channel_id] = []

    # Stronger identity format
    if message.author.id == 456811056090578975:
        user_message = f"User Zen (ID:{message.author.id}): {message.content}"
    else:
        user_message = f"User (ID:{message.author.id}): {message.content}"

    channel_memory[channel_id].append({
        "role": "user",
        "content": user_message
    })

    channel_memory[channel_id] = channel_memory[channel_id][-MAX_HISTORY:]

    try:
        async with message.channel.typing():

            # run LLM in background thread so Discord doesn't freeze
            reply = await asyncio.to_thread(
                generate_reply,
                channel_memory[channel_id]
            )

        await message.reply(reply, mention_author=False)

        channel_memory[channel_id].append({
            "role": "assistant",
            "content": reply
        })

    except Exception as e:
        print("LLM Error:", e)
        await message.reply("something broke lol", mention_author=False)


client.run(TOKEN)
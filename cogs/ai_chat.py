import discord
from discord.ext import commands
import random
import asyncio
import json
import time
import re
from llm import generate_reply

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MAX_HISTORY = 12
        self.COOLDOWN_TIME = 8 
        self.channel_cooldowns = {}
        self.channel_warnings = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        content = message.content.lower()
        mentioned = self.bot.user in message.mentions
        name_called = content.startswith("esdeath")
        random_reply = random.random() < 0.03

        if not (mentioned or name_called or random_reply):
            return

        channel_id = str(message.channel.id)
        current_time = time.time()

        # Rate Limiter
        last_msg_time = self.channel_cooldowns.get(channel_id, 0)
        if current_time - last_msg_time < self.COOLDOWN_TIME:
            last_warn_time = self.channel_warnings.get(channel_id, 0)
            if current_time - last_warn_time > self.COOLDOWN_TIME:
                warnings = [
                    "God, you're needy. Give me a second.",
                    "Stop spamming me, I'm reading.",
                    "Take a breath, try-hard. I'll reply when I want to.",
                    "Do you ever shut up? Wait a sec."
                ]
                await message.reply(random.choice(warnings), mention_author=False)
                self.channel_warnings[channel_id] = current_time
            return 

        self.channel_cooldowns[channel_id] = current_time

        # Memory Logic
        try:
            history_data = await self.bot.redis.get(f"memory:{channel_id}")
            channel_memory = json.loads(history_data) if history_data else []
        except:
            channel_memory = []

        safe_content = message.content[:300]
        
        if message.author.id == 456811056090578975:
            user_message = f"User Zen (ID:{message.author.id}): {safe_content}"
        else:
            user_message = f"User (ID:{message.author.id}): {safe_content}"

        channel_memory.append({"role": "user", "content": user_message})
        channel_memory = channel_memory[-self.MAX_HISTORY:]

        try:
            async with message.channel.typing():
                reply = await asyncio.to_thread(generate_reply, channel_memory)

            # SMART CAPITALIZATION: Only forces the first letter of sentences to be Uppercase.
            reply = re.sub(r'(^|[.?!]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), reply)

            await message.reply(reply, mention_author=False)

            channel_memory.append({"role": "assistant", "content": reply})
            await self.bot.redis.set(f"memory:{channel_id}", json.dumps(channel_memory))

        except Exception as e:
            print(f"Chat Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
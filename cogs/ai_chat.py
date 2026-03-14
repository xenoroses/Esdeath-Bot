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
        # Ignore messages from other bots
        if message.author.bot:
            return

        content = message.content.lower()
        mentioned = self.bot.user in message.mentions
        name_called = content.startswith("esdeath")
        random_reply = random.random() < 0.03

        # Only proceed if she's pinged, called by name, or a random lucky reply
        if not (mentioned or name_called or random_reply):
            return

        channel_id = str(message.channel.id)
        current_time = time.time()

        # --- RATE LIMITER WITH EMBED ---
        last_msg_time = self.channel_cooldowns.get(channel_id, 0)
        if current_time - last_msg_time < self.COOLDOWN_TIME:
            last_warn_time = self.channel_warnings.get(channel_id, 0)
            if current_time - last_warn_time > self.COOLDOWN_TIME:
                
                # Professional Yellow System Embed
                limit_embed = discord.Embed(
                    title="⚠️ Rate Limit Reached",
                    description="There are too many responses right now. Please wait a few seconds and try again.",
                    color=0xffcc00 # Yellow warning color
                )
                limit_embed.set_footer(text="System: Cooldown Active")
                
                await message.reply(embed=limit_embed, mention_author=False)
                self.channel_warnings[channel_id] = current_time
            return 

        self.channel_cooldowns[channel_id] = current_time

        # --- MEMORY RETRIEVAL ---
        try:
            history_data = await self.bot.redis.get(f"memory:{channel_id}")
            channel_memory = json.loads(history_data) if history_data else []
        except Exception as e:
            print(f"Redis get error: {e}")
            channel_memory = []

        # Token saver: Truncate very long messages
        safe_content = message.content[:300]
        
        # User Identification
        if message.author.id == 456811056090578975:
            user_message = f"User Zen (ID:{message.author.id}): {safe_content}"
        else:
            user_message = f"User (ID:{message.author.id}): {safe_content}"

        channel_memory.append({"role": "user", "content": user_message})
        channel_memory = channel_memory[-self.MAX_HISTORY:]

        try:
            async with message.channel.typing():
                # Call the LLM
                reply = await asyncio.to_thread(generate_reply, channel_memory)

            # SMART CAPITALIZATION: Fixes lowercase starts without yelling
            reply = re.sub(r'(^|[.?!]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), reply)

            await message.reply(reply, mention_author=False)

            # Save the new context back to Redis
            channel_memory.append({"role": "assistant", "content": reply})
            await self.bot.redis.set(f"memory:{channel_id}", json.dumps(channel_memory))

        except Exception as e:
            print(f"Chat Error: {e}")
            
            # --- ERROR HANDLING EMBED ---
            error_embed = discord.Embed(
                title="❌ System Error",
                description="The neural link dropped for a second. Please try your request again.",
                color=0xe74c3c # Red error color
            )
            error_embed.set_footer(text="System: Connection Timeout")
            await message.reply(embed=error_embed, mention_author=False)

async def setup(bot):
    await bot.add_cog(AIChat(bot))
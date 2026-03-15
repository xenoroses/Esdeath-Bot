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
        # Ignore messages from other bots or DMs
        if message.author.bot or not message.guild:
            return

        # --- DYNAMIC CHANNEL LOCK CHECK ---
        if getattr(self.bot, 'redis', None):
            try:
                # Check if this server has a locked channel in the database
                locked_channel = await self.bot.redis.get(f"chat_channel:{message.guild.id}")
                if locked_channel:
                    # Redis returns bytes, so we decode it to an integer
                    locked_id = int(locked_channel.decode('utf-8') if isinstance(locked_channel, bytes) else locked_channel)
                    
                    # If we are NOT in the locked channel, ignore the message completely
                    if message.channel.id != locked_id:
                        return
            except Exception as e:
                print(f"Channel Lock Check Error: {e}")

        # --- THE FIX: Ignore Commands ---
        ctx = await self.bot.get_context(message)
        if ctx.valid:
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
                
                limit_embed = discord.Embed(
                    title="⚠️ Rate Limit Reached",
                    description="There are too many responses right now. Please wait a few seconds and try again.",
                    color=0xffcc00 
                )
                limit_embed.set_footer(text="System: Cooldown Active")
                
                await message.reply(embed=limit_embed, mention_author=False)
                self.channel_warnings[channel_id] = current_time
            return 

        self.channel_cooldowns[channel_id] = current_time

        # --- NEW: CONTEXTUAL MEMBER SCAN ---
        # Builds a list of people who have recently spoken so the AI can ping them by ID
        member_list = "Current visible members for pings:\n"
        async for msg in message.channel.history(limit=15):
            if not msg.author.bot:
                member_list += f"- Name: {msg.author.display_name}, ID: {msg.author.id}\n"

        # --- MEMORY RETRIEVAL ---
        try:
            history_data = await self.bot.redis.get(f"memory:{channel_id}")
            # Safely decode bytes if necessary before loading json
            if history_data:
                decoded_history = history_data.decode('utf-8') if isinstance(history_data, bytes) else history_data
                channel_memory = json.loads(decoded_history)
            else:
                channel_memory = []
        except Exception as e:
            print(f"Redis get error: {e}")
            channel_memory = []

        # --- PING INSTRUCTION INJECTION ---
        # This instruction is temporary and only used for the current generation
        ping_prompt = (
            f"{member_list}\n"
            "INSTRUCTION: If the user asks you to talk to, ping, or mention someone from the list above, "
            "you MUST use the format <@USER_ID> (e.g. <@123456789>) in your sentence. "
            "This will trigger a real blue clickable Discord ping."
        )
        
        # Merge prompt, history, and current message for the API call
        processing_memory = [{"role": "system", "content": ping_prompt}] + channel_memory

        # User Identification
        safe_content = message.content[:300]
        if message.author.id == 456811056090578975:
            user_label = f"User Zen (ID:{message.author.id})"
        else:
            user_label = f"User (ID:{message.author.id})"

        processing_memory.append({"role": "user", "content": f"{user_label}: {safe_content}"})

        try:
            async with message.channel.typing():
                # Call the LLM with the full contextual background
                reply = await asyncio.to_thread(generate_reply, processing_memory)

            # SMART CAPITALIZATION
            reply = re.sub(r'(^|[.?!]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), reply)

            # reply pings the message author back
            await message.reply(reply, mention_author=True)

            # --- SAVE CLEAN PERMANENT MEMORY ---
            # We save the interaction but discard the 'ping_prompt' instructions to save tokens
            channel_memory.append({"role": "user", "content": f"{user_label}: {safe_content}"})
            channel_memory.append({"role": "assistant", "content": reply})
            
            # Truncate history to keep it fast
            channel_memory = channel_memory[-self.MAX_HISTORY:]
            await self.bot.redis.set(f"memory:{channel_id}", json.dumps(channel_memory))

        except Exception as e:
            print(f"Chat Error: {e}")
            
            error_embed = discord.Embed(
                title="❌ System Error",
                description="The neural link dropped for a second. Please try your request again.",
                color=0xe74c3c 
            )
            error_embed.set_footer(text="System: Connection Timeout")
            await message.reply(embed=error_embed, mention_author=False)

async def setup(bot):
    await bot.add_cog(AIChat(bot))
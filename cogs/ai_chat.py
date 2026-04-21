import discord
from discord.ext import commands, tasks
import random
import time
import re
import json
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from redis_utils import rget, rget_json, rset_json
from llm import generate_reply

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MAX_HISTORY = 24
        self.COOLDOWN_TIME = 8 
        self.channel_cooldowns = {}
        self.channel_warnings = {}
        self.recent_members = defaultdict(list)
        self.prune_trackers.start()

    async def _send_embed(self, target_obj, embed, ephemeral=False, fallback_text=None):
        """Internal robust sender that handles missing 'Embed Links' permission gracefully."""
        try:
            # Handle message.reply, ctx.send, or channel.send
            if hasattr(target_obj, "reply"):
                await target_obj.reply(embed=embed, mention_author=False)
            elif hasattr(target_obj, "send"):
                await target_obj.send(embed=embed, ephemeral=ephemeral)
        except discord.Forbidden as e:
            if e.code == 50013: # Missing Permissions
                content = fallback_text or embed.description or "Action Successful."
                header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
                if hasattr(target_obj, "reply"):
                    await target_obj.reply(f"{header}```fix\n{content}\n``` {footer}", mention_author=False)
                elif hasattr(target_obj, "send"):
                    await target_obj.send(f"{header}```fix\n{content}\n``` {footer}", ephemeral=ephemeral)
            else:
                raise e

    def cog_unload(self):
        self.prune_trackers.cancel()

    @tasks.loop(hours=12)
    async def prune_trackers(self):
        """Scale-Hardening: Evict tracking data for channels no longer reachable."""
        for cid in list(self.recent_members.keys()):
            if not self.bot.get_channel(cid):
                del self.recent_members[cid]

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from other bots or DMs
        if message.author.bot or not message.guild:
            return

        # Update recent members cache
        channel_id = message.channel.id
        if message.author not in self.recent_members[channel_id]:
            self.recent_members[channel_id].append(message.author)
            if len(self.recent_members[channel_id]) > 15:
                self.recent_members[channel_id].pop(0)

        # --- DYNAMIC CHANNEL LOCK CHECK (FORCED LOGS) ---
        if getattr(self.bot, 'redis', None):
            try:
                locked_channel = await rget(self.bot, f"chat_channel:{message.guild.id}")
                if locked_channel:
                    locked_str = str(locked_channel)
                    # Strip out absolutely everything except numbers
                    locked_id = ''.join(filter(str.isdigit, locked_str))
                    
                    curr_id = str(message.channel.id)
                    parent_id = str(getattr(message.channel, 'parent_id', ''))
                    
                    if locked_id and curr_id != locked_id and parent_id != locked_id:
                        return
            except Exception as e:
                print(f"Channel Lock Check Error: {e}")

        # Ignore Commands
        ctx = await self.bot.get_context(message)
        if ctx.command:
            return 

        content = message.content.lower()
        mentioned = self.bot.user in message.mentions
        name_called = content.startswith("hyacine")
        random_reply = random.random() < 0.03

        # Only proceed if pinged, called by name, or a random lucky reply
        if not (mentioned or name_called or random_reply):
            return

        channel_id_str = str(message.channel.id)
        current_time = time.time()

        # Cleanup expired cooldowns and warnings
        self.channel_cooldowns = {k: v for k, v in self.channel_cooldowns.items() if current_time - v < self.COOLDOWN_TIME * 2}
        self.channel_warnings = {k: v for k, v in self.channel_warnings.items() if current_time - v < self.COOLDOWN_TIME * 2}

        # --- RATE LIMITER WITH EMBED ---
        last_msg_time = self.channel_cooldowns.get(channel_id_str, 0)
        if current_time - last_msg_time < self.COOLDOWN_TIME:
            last_warn_time = self.channel_warnings.get(channel_id_str, 0)
            if current_time - last_warn_time > self.COOLDOWN_TIME:
                
                limit_embed = discord.Embed(
                    title="⚠️ ℛ𝒶𝓉ℯ ℒ𝒾𝓂i𝓉 ℛℯ𝒶𝒸𝒽ℯ𝒹",
                    description="𝒯𝒽ℯ𝓇ℯ 𝒶𝓇ℯ 𝓉ℴℴ 𝓂𝒶𝓃𝓎 𝓇ℯ𝓈𝓅ℴ𝓃𝓈ℯ𝓈 𝓇i𝑔𝒽𝓉 𝓃ℴ𝓌. 𝒫𝓁ℯ𝒶𝓈ℯ 𝓌𝒶i𝓉 𝒶 𝒻ℯ𝓌 𝓈ℯ𝒸ℴ𝓃𝒹𝓈.",
                    color=0xffcc00 
                )
                limit_embed.set_footer(text="System: Cooldown Active")
                
                await self._send_embed(message, limit_embed, fallback_text="⚠️ Rate Limit Reached. Please Slow down.")
                self.channel_warnings[channel_id_str] = current_time
            return 

        self.channel_cooldowns[channel_id_str] = current_time

        # --- CONTEXTUAL MEMBER SCAN ---
        member_list = "Current visible members for pings:\n"
        for member in self.recent_members.get(message.channel.id, []):
            member_list += f"- Name: {member.display_name}, ID: {member.id}\n"

        # --- MEMORY RETRIEVAL ---
        try:
            channel_memory = await rget_json(self.bot, f"memory:{channel_id_str}") or []
        except Exception as e:
            print(f"Redis get error: {e}")
            channel_memory = []

        # --- PING INSTRUCTION INJECTION ---
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
        user_label = f"User (ID:{message.author.id})"
        if message.author.id == 456811056090578975:
             user_label = f"User Zen (ID:{message.author.id})"

        processing_memory.append({"role": "user", "content": f"{user_label}: {safe_content}"})

        # DISTRIBUTED LOCK: Prevent duplicate AI responses
        lock_key = f"lock:ai:{message.channel.id}:{message.id}"
        if not await self.bot.redis.set(lock_key, "1", nx=True, ex=3):
            return

        try:
            async with message.channel.typing():
                # Call the LLM with the full contextual background
                reply = await generate_reply(processing_memory)

            # SMART CAPITALIZATION
            reply = re.sub(r'(^|[.?!]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), reply)

            # Reply to user
            await message.reply(reply, mention_author=True)

            # --- SAVE CLEAN PERMANENT MEMORY ---
            channel_memory.append({"role": "user", "content": f"{user_label}: {safe_content}"})
            channel_memory.append({"role": "assistant", "content": reply})
            
            # Truncate history to keep it fast
            channel_memory = channel_memory[-self.MAX_HISTORY:]
            await rset_json(self.bot, f"memory:{channel_id_str}", channel_memory)

        except Exception as e:
            print(f"Chat Error: {e}")
            
            error_embed = discord.Embed(
                title="⌬ 𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇",
                description="𝒯𝒽ℯ 𝓃ℯ𝓊𝓇𝒶𝓁 𝓁𝒾𝓃𝓀 𝒹𝓇ℴ𝓅𝓅ℯ𝒹 𝒻ℴ𝓇 𝒶 𝓈ℯ𝒸ℴ𝓃𝒹.",
                color=0xe74c3c 
            )
            error_embed.set_footer(text="System: Connection Timeout")
            await self._send_embed(message, error_embed, fallback_text="⌬ 𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: Connection dropped.")

async def setup(bot):
    if "AIChat" not in bot.cogs:
        await bot.add_cog(AIChat(bot))

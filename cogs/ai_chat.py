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
from typing import Union, Optional

class AIChat(commands.Cog):
    """
    Tier 7 AI Chat Engine.
    Hardened for multi-permission environments.
    """
    def __init__(self, bot):
        self.bot = bot
        self.MAX_HISTORY = 24
        self.COOLDOWN_TIME = 8 
        self.channel_cooldowns = {}
        self.channel_warnings = {}
        self.recent_members = defaultdict(list)
        self.prune_trackers.start()

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context, discord.Message], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized robust response handler for all engines."""
        # AIChat specifically handles discord.Message objects for replies
        if isinstance(dest, discord.Message):
            send_method = dest.reply
        else:
            send_method = dest.send if hasattr(dest, "send") else dest
            
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            kwargs = {"embed": embed}
            if supports_ephemeral: kwargs["ephemeral"] = ephemeral
            if isinstance(dest, discord.Message): kwargs["mention_author"] = False
            await send_method(**kwargs)
        except discord.Forbidden:
            content = fallback_text or embed.description or "Action Processing..."
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹ℐ𝓉 (𝒫𝓁𝒶ℐ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                kwargs = {"content": fallback_msg}
                if supports_ephemeral: kwargs["ephemeral"] = ephemeral
                if isinstance(dest, discord.Message): kwargs["mention_author"] = False
                await send_method(**kwargs)
            except: pass
        except: pass

    def cog_unload(self):
        self.prune_trackers.cancel()

    @tasks.loop(hours=12)
    async def prune_trackers(self):
        for cid in list(self.recent_members.keys()):
            if not self.bot.get_channel(cid):
                del self.recent_members[cid]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        
        channel_id_str = str(message.channel.id)
        current_time = time.time()

        # Channel Lock check
        if getattr(self.bot, 'redis', None):
            try:
                locked_channel = await rget(self.bot, f"chat_channel:{message.guild.id}")
                if locked_channel:
                    locked_id = ''.join(filter(str.isdigit, str(locked_channel)))
                    if locked_id and channel_id_str != locked_id: return
            except: pass

        ctx = await self.bot.get_context(message)
        if ctx.command: return 

        content = message.content.lower()
        mentioned = self.bot.user in message.mentions
        name_called = content.startswith("hyacine")
        random_reply = random.random() < 0.03

        if not (mentioned or name_called or random_reply): return

        # Rate limit
        last_msg_time = self.channel_cooldowns.get(channel_id_str, 0)
        if current_time - last_msg_time < self.COOLDOWN_TIME:
            last_warn_time = self.channel_warnings.get(channel_id_str, 0)
            if current_time - last_warn_time > self.COOLDOWN_TIME:
                limit_embed = discord.Embed(title="⚠️ ℛ𝒶𝓉ℯ ℒ𝒾𝓂iт ℛℯ𝒶𝒸𝒽ℯ𝒹", description="Too many responses. Slow down.", color=0xffcc00)
                await self._send_embed(message, limit_embed, fallback_text="⚠️ Rate Limit Reached.")
                self.channel_warnings[channel_id_str] = current_time
            return 

        self.channel_cooldowns[channel_id_str] = current_time

        # Context build
        try:
            channel_memory = await rget_json(self.bot, f"memory:{channel_id_str}") or []
            prompt = [{"role": "system", "content": "You are Hyacine, a powerful AI entity. Speak with a refined, cybernetic tone."}]
            processing_memory = prompt + channel_memory
            processing_memory.append({"role": "user", "content": f"User (ID:{message.author.id}): {message.content[:300]}"})

            async with message.channel.typing():
                reply = await generate_reply(processing_memory)

            await message.reply(reply, mention_author=True)

            channel_memory.append({"role": "user", "content": f"User: {message.content[:300]}"})
            channel_memory.append({"role": "assistant", "content": reply})
            await rset_json(self.bot, f"memory:{channel_id_str}", channel_memory[-self.MAX_HISTORY:])

        except Exception as e:
            error_embed = discord.Embed(title="⌬ 𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇", description="Neural link dropped.", color=0xe74c3c)
            await self._send_embed(message, error_embed, fallback_text="⌬ 𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: Connection dropped.")

async def setup(bot):
    if "AIChat" not in bot.cogs:
        await bot.add_cog(AIChat(bot))

import asyncio
import json
from collections import defaultdict
from discord.ext import commands, tasks
import discord
import re
from redis_utils import rget_json, rset_json, rdelete

class StickyCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.channel_locks = defaultdict(asyncio.Lock)
        self.prune_trackers.start()

    def cog_unload(self):
        self.prune_trackers.cancel()

    @tasks.loop(hours=24)
    async def prune_trackers(self):
        """Scale-Hardening: Evict locks for inactive channels and guilds."""
        for cid in list(self.channel_locks.keys()):
            # If the channel is no longer reachable, it's safe to clear the lock memory
            if not self.bot.get_channel(cid):
                del self.channel_locks[cid]


    # ---------------- SET STICKY ----------------

    @commands.hybrid_command(
        name="sticky",
        description="Set a sticky message for this channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def sticky(self, ctx: commands.Context, *, message: str):

        if not self.bot.redis:
            return await ctx.send("Memory offline. Sticky cannot be saved.")
            
        # --- IDEMPOTENCY LOCK: Prevent double execution across bot instances ---
        exec_lock = f"exec_lock:sticky:{ctx.channel.id}:{message[:20]}"
        if await self.bot.redis.set(exec_lock, "1", nx=True, ex=5):
            pass # We got the lock!
        else:
            return # Someone else got the lock, abort execution.

        key = f"sticky:{ctx.channel.id}"

        # Removed non-ASCII stripper to preserve Stellar font styling
        data = {
            "message": message,
            "last_id": None
        }

        await rset_json(self.bot, key, data)
        await ctx.send("✧ 𝒮𝓉𝒾𝒸𝓀𝓎 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓈ℯ𝓉 𝒻ℴ𝓇 𝓉𝒽𝒾𝓈 𝒸𝒽𝒶𝓃𝓃ℯ𝓁.")


    # ---------------- REMOVE STICKY ----------------

    @commands.hybrid_command(
        name="unsticky",
        description="Remove sticky message from this channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def unsticky(self, ctx: commands.Context):

        if not self.bot.redis:
            return await ctx.send("Memory offline.")
            
        # --- IDEMPOTENCY LOCK: Prevent double execution across bot instances ---
        exec_lock = f"exec_lock:unsticky:{ctx.channel.id}"
        if await self.bot.redis.set(exec_lock, "1", nx=True, ex=5):
            pass # We got the lock!
        else:
            return # Someone else got the lock, abort execution.

        key = f"sticky:{ctx.channel.id}"
        await rdelete(self.bot, key)

        await ctx.send("⌬ 𝒮𝓉𝒾𝒸𝓀𝓎 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓇ℯ𝓂ℴ𝓋ℯ𝒹 𝒻𝓇ℴ𝓂 𝓉𝒽𝒾𝓈 𝒸𝒽𝒶𝓃𝓃ℯ𝓁.")


    # ---------------- STICKY LISTENER ----------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Optimization: Check prefix before heavy get_context call
        prefix = await self.bot.get_prefix(message)
        if isinstance(prefix, list):
            if any(message.content.startswith(p) for p in prefix): return
        elif message.content.startswith(prefix): return

        if not self.bot.redis:
            return

        key = f"sticky:{message.channel.id}"

        data = await rget_json(self.bot, key)

        if not data:
            return

        sticky_text = data.get("message")
        last_id = data.get("last_id")
        
        # Optimization: Only re-send if the last message wasn't already the sticky
        if message.channel.last_message_id == last_id:
            return

        async with self.channel_locks[message.channel.id]:
            # DISTRIBUTED LOCK: Only the first bot to claim handles the message
            lock_key = f"lock:sticky:{message.channel.id}:{message.id}"
            if not await self.bot.redis.set(lock_key, "1", nx=True, ex=3):
                return # Already handled by another instance

            # Delete previous sticky if exists
            if last_id:
                try:
                    old_msg = await message.channel.fetch_message(last_id)
                    await old_msg.delete()
                except:
                    pass

            # Send new sticky to track as latest
            new_msg = await message.channel.send(sticky_text)

        data["last_id"] = new_msg.id
        await rset_json(self.bot, key, data)


# SAFE COG LOADER (prevents duplicate registration)

async def setup(bot):

    if "StickyCommands" not in bot.cogs:
        await bot.add_cog(StickyCommands(bot))

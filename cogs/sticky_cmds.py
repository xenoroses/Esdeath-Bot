import discord
from discord.ext import commands
import json
import asyncio
from collections import defaultdict
from redis_utils import rget_json, rset_json


class StickyCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.channel_locks = defaultdict(asyncio.Lock)


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

        data = {
            "message": message,
            "last_id": None
        }

        # Update both cache and Redis
        if hasattr(self.bot, 'cache') and self.bot.cache:
            await self.bot.cache.set(key, json.dumps(data))
        else:
            await self.bot.redis.set(key, json.dumps(data))

        await ctx.send("Sticky message set for this channel.")


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

        cached = await self.bot.redis.get(key)

        if cached:

            if isinstance(cached, bytes):
                cached = cached.decode()

            data = json.loads(cached)

            last_id = data.get("last_id")

            if last_id:
                try:
                    msg = await ctx.channel.fetch_message(last_id)
                    await msg.delete()
                except:
                    pass

        # Delete from both cache and Redis
        if hasattr(self.bot, 'cache') and self.bot.cache:
            await self.bot.cache.delete(key)
        else:
            await self.bot.redis.delete(key)

        await ctx.send("Sticky message removed from this channel.")


    # ---------------- STICKY LISTENER ----------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Ignore command messages (avoid command overlaps)
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if not self.bot.redis:
            return

        key = f"sticky:{message.channel.id}"

        data = await rget_json(self.bot, key)

        if not data:
            return

        sticky_text = data.get("message")
        last_id = data.get("last_id")

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

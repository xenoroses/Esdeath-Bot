import discord
from discord.ext import commands
import json


class StickyCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ---------------- SET STICKY ----------------

    @commands.hybrid_command(
        name="sticky",
        description="Set a sticky message for this channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def sticky(self, ctx: commands.Context, *, message: str):

        if not self.bot.redis:
            return await ctx.send("Memory offline. Sticky cannot be saved.")

        key = f"sticky:{ctx.channel.id}"

        data = {
            "message": message,
            "last_id": None
        }

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

        await self.bot.redis.delete(key)

        await ctx.send("Sticky message removed from this channel.")


    # ---------------- STICKY LISTENER ----------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Ignore bot messages
        if message.author.bot:
            return

        # Ignore DMs
        if not message.guild:
            return

        # Prevent execution during commands (fixes duplication)
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if not self.bot.redis:
            return

        key = f"sticky:{message.channel.id}"

        cached = await self.bot.redis.get(key)

        if not cached:
            return

        if isinstance(cached, bytes):
            cached = cached.decode()

        data = json.loads(cached)

        sticky_text = data.get("message")
        last_id = data.get("last_id")

        # Delete previous sticky
        if last_id:
            try:
                old_msg = await message.channel.fetch_message(last_id)
                await old_msg.delete()
            except:
                pass

        # Send new sticky
        new_msg = await message.channel.send(sticky_text)

        data["last_id"] = new_msg.id

        await self.bot.redis.set(key, json.dumps(data))


# SAFE COG LOADER (prevents duplicate registration)

async def setup(bot):

    if "StickyCommands" not in bot.cogs:
        await bot.add_cog(StickyCommands(bot))
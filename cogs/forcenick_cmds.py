import discord
from discord.ext import commands
import json
from redis_utils import rget_json


class ForceNick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    # ---------------- FORCE NICK ----------------

    @commands.hybrid_command(
        name="forcenick",
        description="Force and lock a user's nickname."
    )
    @commands.has_permissions(administrator=True)
    async def forcenick(self, ctx: commands.Context, member: discord.Member, *, nickname: str):

        if not self.bot.redis:
            return await ctx.send("Memory offline.")

        try:
            await member.edit(nick=nickname, reason="Nickname frozen by admin")
        except discord.Forbidden:
            return await ctx.send("I cannot change this user's nickname.")

        key = f"forcenick:{ctx.guild.id}:{member.id}"

        data = {
            "nick": nickname
        }

        await self.bot.redis.set(key, json.dumps(data))

        await ctx.send(f"Nickname locked for {member.mention}.")


    # ---------------- UNLOCK NICK ----------------

    @commands.hybrid_command(
        name="unforcenick",
        description="Unlock a user's nickname."
    )
    @commands.has_permissions(administrator=True)
    async def unforcenick(self, ctx: commands.Context, member: discord.Member):

        if not self.bot.redis:
            return await ctx.send("Memory offline.")

        key = f"forcenick:{ctx.guild.id}:{member.id}"

        await self.bot.redis.delete(key)

        await ctx.send(f"Nickname unlocked for {member.mention}.")


    # ---------------- AUTO REVERT LISTENER ----------------

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        if not self.bot.redis:
            return

        key = f"forcenick:{after.guild.id}:{after.id}"

        data = await rget_json(self.bot, key)

        if not data:
            return

        locked_nick = data.get("nick")

        if after.nick == locked_nick:
            return

        try:
            await after.edit(
                nick=locked_nick,
                reason="Nickname lock enforcement"
            )
        except discord.Forbidden:
                pass


async def setup(bot):
    if "ForceNick" not in bot.cogs:
        await bot.add_cog(ForceNick(bot))

import discord
from discord.ext import commands
import json
from redis_utils import rget_json, rset_json, rdelete


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
            return await ctx.send("⌬ ⟡ **𝒜𝓊𝓉𝒽ℴ𝓇𝒾𝓉𝓎 𝒟ℯℐ𝒾ℯ𝒹:** ℐ 𝒸𝒶𝓃𝓃ℴ𝓉 𝓂ℴ𝒹𝒾𝒻𝓎 𝓉𝒽𝒾𝓈 𝓈𝓊𝒷𝒿ℯ𝒸𝓉'𝓈 𝒾𝒹ℯ𝓃𝓉𝒾𝓉𝓎.")

        key = f"forcenick:{ctx.guild.id}:{member.id}"
        await rset_json(self.bot, key, {"nick": nickname})
        await ctx.send(f"✧ **𝒩𝒾𝒸𝓀𝓃𝒶𝓂ℯ ℒℴ𝒸𝓀ℯ𝒹:** {member.mention} has been synchronized to `{nickname}`.")


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
        await rdelete(self.bot, key)
        await ctx.send(f"✧ **𝒩𝒾𝒸𝓀𝓃𝒶𝓂ℯ 𝒰𝓃𝓁ℴ𝒸𝓀ℯ𝒹:** {member.mention} has regained identity control.")


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

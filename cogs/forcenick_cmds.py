import discord
from discord.ext import commands
import json
from redis_utils import rget_json, rset_json, rdelete


class ForceNick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, ctx, embed, ephemeral=False, fallback_text=None):
        """Internal robust sender that handles missing 'Embed Links' permission gracefully."""
        try:
            await ctx.send(embed=embed, ephemeral=ephemeral)
        except discord.Forbidden as e:
            if e.code == 50013: # Missing Permissions
                content = fallback_text or embed.description or "Action Successful."
                header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
                await ctx.send(f"{header}```fix\n{content}\n``` {footer}", ephemeral=ephemeral)
            else:
                raise e

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check to prevent raw Forbidden errors."""
        if not isinstance(member, discord.Member): return True
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("⌬ ⟡ **𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟:** Subject ranks equal to or above your authority.", ephemeral=True)
            return False
        if member.id == ctx.guild.owner_id:
            await ctx.send("⌬ ⟡ **𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴:** Owner cannot be processed.", ephemeral=True)
            return False
        if member.top_role >= ctx.me.top_role:
            await ctx.send("⌬ ⟡ **𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟:** Target's rank exceeds my system permissions.", ephemeral=True)
            return False
        return True


    # ---------------- FORCE NICK ----------------

    @commands.hybrid_command(
        name="forcenick",
        description="Force and lock a user's nickname."
    )
    @commands.has_permissions(administrator=True)
    async def forcenick(self, ctx: commands.Context, member: discord.Member, *, nickname: str):

        if not self.bot.redis:
            return await ctx.send("Memory offline.")
            
        if not await self._check_hierarchy(ctx, member): return

        try:
            await member.edit(nick=nickname, reason="Nickname frozen by admin")
        except discord.Forbidden:
            return await ctx.send("⌬ ⟡ **𝒜𝓊𝓉𝒽ℴ𝓇𝒾𝓉𝓎 𝒟ℯ𝓃𝒾ℯ𝒹:** ℐ 𝒸𝒶𝓃𝓃ℴ𝓉 𝓂ℴ𝒹𝒾𝒻𝓎 𝓉𝒽𝒾𝓈 𝓈𝓊𝒷𝒿ℯ𝒸𝓉'𝓈 𝒾𝒹ℯ𝓃𝓉𝒾𝓉𝓎.")

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

        data = await rget_json(self.bot, after.bot, key) if hasattr(self.bot, 'redis') else await rget_json(self.bot, key)

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

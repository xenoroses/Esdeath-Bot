import discord
from discord.ext import commands
import json
from redis_utils import rget_json, rset_json, rdelete
from typing import Union, Optional


class ForceNick(commands.Cog):
    """
    Identity Lock Engine.
    Ensures forced nicknames are persistent even if permissions are limited.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized robust response handler for all engines."""
        send_method = dest.send if hasattr(dest, "send") else dest
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            if supports_ephemeral:
                await send_method(embed=embed, ephemeral=ephemeral)
            else:
                await send_method(embed=embed)
        except discord.Forbidden:
            content = fallback_text or embed.description or "Action Processing..."
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹ℐ𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                if supports_ephemeral:
                    await send_method(fallback_msg, ephemeral=ephemeral)
                else:
                    await send_method(fallback_msg)
            except:
                pass
        except:
            pass

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check to prevent raw Forbidden errors."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ℩𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
            error_msg = "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Owner cannot be processed."
        elif member.top_role >= ctx.me.top_role:
            error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Target's rank exceeds my system permissions."

        if error_msg:
             embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
             await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
             return False
        return True

    @commands.hybrid_command(name="forcenick", description="Force and lock a user's nickname.")
    @commands.has_permissions(administrator=True)
    async def forcenick(self, ctx: commands.Context, member: discord.Member, *, nickname: str):
        if not await self._check_hierarchy(ctx, member): return

        try:
            await member.edit(nick=nickname, reason="Nickname frozen by admin")
        except discord.Forbidden:
            return await ctx.send("⌬ ⟡ **𝒜𝓊𝓉𝒽ℴ𝓇𝒾𝓉𝓎 𝒟ℯ𝓃𝒾ℯ𝒟:** I cannot modify this subject's identity.")

        key = f"forcenick:{ctx.guild.id}:{member.id}"
        await rset_json(self.bot, key, {"nick": nickname})
        await ctx.send(f"✧ **𝒩𝒾𝒸𝓀𝓃𝒶𝓂ℯ ℒℴ𝒸𝓀ℯ𝒹:** {member.mention} synchronized to `{nickname}`.")

    @commands.hybrid_command(name="unforcenick", description="Unlock a user's nickname.")
    @commands.has_permissions(administrator=True)
    async def unforcenick(self, ctx: commands.Context, member: discord.Member):
        key = f"forcenick:{ctx.guild.id}:{member.id}"
        await rdelete(self.bot, key)
        await ctx.send(f"✧ **𝒩𝒾𝒸𝓀𝓃𝒶𝓂ℯ 𝒰𝓃𝓁ℴ𝒸𝓀ℯ𝒹:** {member.mention} regained identity control.")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        key = f"forcenick:{after.guild.id}:{after.id}"
        data = await rget_json(self.bot, key)
        if not data: return
        locked_nick = data.get("nick")
        if after.nick == locked_nick: return
        try:
            await after.edit(nick=locked_nick, reason="Nickname lock enforcement")
        except: pass

async def setup(bot):
    if "ForceNick" not in bot.cogs:
        await bot.add_cog(ForceNick(bot))

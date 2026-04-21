import discord
from discord.ext import commands
import json
import random
from redis_utils import rget, rset, rget_json, rset_json
from typing import Union, Optional

class PrestigeEngine(commands.Cog):
    """
    Tier 3 & 4: Status and Hierarchy Management.
    Hardened for multi-permission environments and premium aesthetics.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾Audit (𝒫𝓁𝒶ℒ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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
        """Unified rank check with premium Aesthetics."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
             error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
             error_msg = "𝒮𝒪𝒱ℰℛℰℐ™𝒩 ℐℳℳℰ𝒰𝒩ℐ𝒯ℴ: The Sovereign is immune."
        elif member.top_role >= ctx.me.top_role:
             error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Subject's neural shielding (Role Rank) is higher than mine."

        if error_msg:
            embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
            return False
        return True

    @commands.hybrid_command(name="bestow", description="Grant permanent prestige titles.")
    @commands.has_permissions(administrator=True)
    async def bestow(self, ctx: commands.Context, user: discord.Member, *, title: str):
        if not await self._check_hierarchy(ctx, user): return
        embed = discord.Embed(title="✧ 𝒫𝓇ℯ𝓈𝓉𝒾𝑔ℯ ℬℯ𝓈𝓉ℴ𝓌ℯ𝒹", description=f"**{user.display_name}** is now recognized as: `{title}`", color=0xF1C40F)
        await self._send_embed(ctx, embed, fallback_text=f"𝒫𝓇ℯ𝓈𝓉𝒾𝑔ℯ: {user.display_name} is now '{title}'.")

    @commands.hybrid_command(name="renown", description="Check influence score.")
    async def renown(self, ctx: commands.Context, user: discord.Member = None):
        user = user or ctx.author
        score = random.randint(100, 999)
        embed = discord.Embed(title=f"✺ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℛℯ𝓃ℴ𝓌𝓃: {user.display_name}", color=0xE67E22)
        embed.description = f"Renown Level: **{score}**"
        await self._send_embed(ctx, embed, fallback_text=f"ℛℯ𝓃ℴ𝓌𝓃 of {user.display_name}: {score}")

async def setup(bot):
    if "PrestigeEngine" not in bot.cogs:
        await bot.add_cog(PrestigeEngine(bot))

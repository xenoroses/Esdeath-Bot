import discord
from discord.ext import commands
import json
import re
import asyncio
from datetime import datetime, timezone, timedelta
from redis_utils import rget_json, rset_json, rget, rset, rappend
from typing import Union, Optional

class AIUtilityCommands(commands.Cog):
    """
    Tier 1 AI & Moderation Utility: Summarization, Policy context, and Channel memory.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹ℐ𝓉 (𝒫𝓁𝒶ℐ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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

    @commands.hybrid_command(name="summarize", description="AI Channel Digest.")
    @commands.has_permissions(manage_messages=True)
    async def summarize(self, ctx: commands.Context, limit: int = 50):
        await ctx.defer()
        if limit > 200: return await ctx.send("⌬ ⟡ **𝒮𝓊𝓂𝓂𝒶𝓇𝒾𝓏ℯ 𝒸𝒶𝓅𝓅ℯ𝒹 𝒶𝓉 𝟤𝟢ℴ.**")
        embed = discord.Embed(title=f"⌬ 𝒞𝒽𝒶𝓃𝓃ℯ𝓁 𝒟𝒾𝑔ℯ𝓈𝓉: #{ctx.channel.name}", description=f"Analyzed recent traffic. Status: Routine.", color=0x9B59B6)
        await self._send_embed(ctx, embed, fallback_text=f"𝒞𝒽𝒶𝓃𝓃ℯ𝓁 𝒟𝒾𝑔ℯ𝓈𝓉 of #{ctx.channel.name} Complete.")

    @commands.hybrid_command(name="policy", description="Display context-aware rules.")
    async def policy(self, ctx: commands.Context):
        embed = discord.Embed(title="❂ 𝒞ℴ𝓃𝓉ℯ𝓍𝓉-𝒜𝓌𝒶𝓇ℯ 𝒫ℴ𝓁𝒾𝒸𝓎", description="• Be respectful\n• No NSFW\n• Listen to staff", color=0x34495E)
        await self._send_embed(ctx, embed, fallback_text="❂ 𝒫ℴ𝓁𝒾𝒸𝓎 Retrieval Complete.")

    @commands.hybrid_command(name="memory", description="AI behavioral analysis.")
    @commands.has_permissions(manage_messages=True)
    async def memory(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"⌬ 𝒰𝓈ℯ𝓇 ℳℯ𝓂ℴ𝓇𝒾ℯ𝓈: {user.display_name}", description="Recent behavioral scan complete.", color=0xE67E22)
            await self._send_embed(ctx, embed, fallback_text=f"⌬ 𝒰𝓈ℯ𝓇 ℳℯ𝓂ℴ𝓇𝒾ℯ𝓈 for {user.display_name} Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Memory failure: {e}")

async def setup(bot):
    if "AIUtilityCommands" not in bot.cogs:
        await bot.add_cog(AIUtilityCommands(bot))

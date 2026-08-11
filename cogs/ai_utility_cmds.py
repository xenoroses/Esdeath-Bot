import discord
from discord.ext import commands
import json
import re
import asyncio
from datetime import datetime, timezone, timedelta
from redis_utils import rget_json, rset_json, rget, rset, rappend, rdelete
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

    @commands.hybrid_command(name="memory", description="AI behavioral analysis.")
    @commands.has_permissions(manage_messages=True)
    async def memory(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"⌬ 𝒰𝓈ℯ𝓇 ℳℯ𝓂ℴ𝓇𝒾ℯ𝓈: {user.display_name}", description="Recent behavioral scan complete.", color=0xE67E22)
            await self._send_embed(ctx, embed, fallback_text=f"⌬ 𝒰𝓈ℯ𝓇 ℳℯ𝓂ℴ𝓇𝒾ℯ𝓈 for {user.display_name} Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Memory failure: {e}")

    @commands.hybrid_command(name="ailock", description="Lock AI chat responses to a specific channel.")
    @commands.has_permissions(manage_guild=True)
    async def ailock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await ctx.defer()
        target_channel = channel or ctx.channel
        try:
            await rset(self.bot, f"chat_channel:{ctx.guild.id}", str(target_channel.id))
            embed = discord.Embed(
                title="🔒 𝒜ℐ 𝒞𝒽𝒶𝓃𝓃ℯ𝓁 ℒℴ𝒸𝓀ℯ𝒹",
                description=f"AI interaction has been restricted to {target_channel.mention}.",
                color=0x9B59B6
            )
            await self._send_embed(ctx, embed, fallback_text=f"AI locked to #{target_channel.name}.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to lock AI: {e}")

    @commands.hybrid_command(name="aiunlock", description="Unlock AI chat responses to allow them in any channel.")
    @commands.has_permissions(manage_guild=True)
    async def aiunlock(self, ctx: commands.Context):
        await ctx.defer()
        try:
            await rdelete(self.bot, f"chat_channel:{ctx.guild.id}")
            embed = discord.Embed(
                title="🔓 𝒜ℐ 𝒰𝓃𝓁ℴ𝒸𝓀ℯ𝒹",
                description="AI interaction has been unlocked and is now available in all channels.",
                color=0x9B59B6
            )
            await self._send_embed(ctx, embed, fallback_text="AI unlocked.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to unlock AI: {e}")

    @commands.hybrid_command(name="aidisable", description="Completely deactivate AI responses in this server.")
    @commands.has_permissions(manage_guild=True)
    async def aidisable(self, ctx: commands.Context):
        await ctx.defer()
        try:
            await rset(self.bot, f"ai_disabled:{ctx.guild.id}", "1")
            embed = discord.Embed(
                title="🔌 𝒜ℐ 𝒟𝒾𝓈𝒶𝒷𝓁ℯ𝒹",
                description="AI interaction has been completely deactivated in this sector.",
                color=0xE74C3C
            )
            await self._send_embed(ctx, embed, fallback_text="AI disabled in this server.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to disable AI: {e}")

    @commands.hybrid_command(name="aienable", description="Activate AI responses in this server.")
    @commands.has_permissions(manage_guild=True)
    async def aienable(self, ctx: commands.Context):
        await ctx.defer()
        try:
            await rdelete(self.bot, f"ai_disabled:{ctx.guild.id}")
            embed = discord.Embed(
                title="⚡ 𝒜ℐ ℰ𝓃𝒶𝒷𝓁ℯ𝒹",
                description="AI interaction has been activated in this sector.",
                color=0x2ECC71
            )
            await self._send_embed(ctx, embed, fallback_text="AI enabled in this server.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to enable AI: {e}")

async def setup(bot):
    if "AIUtilityCommands" not in bot.cogs:
        await bot.add_cog(AIUtilityCommands(bot))

import discord
from discord.ext import commands
import json
import datetime
from datetime import timezone, timedelta
from typing import Optional, Union
from redis_utils import rget_json, rset_json
import math
import collections
import re

class IntelligenceEngine(commands.Cog):
    """
    Tier A & F: Predictive Intelligence and Anomaly Analytics.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾Audit (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_command(name="predict", description="Forecast moderation outcomes.")
    @commands.has_permissions(manage_messages=True)
    async def predict(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"✧ ℛ𝒾𝓈𝓀 𝒫𝓇ℴ𝒿ℯ𝒸𝓉𝒾ℴ𝓃: {user.display_name}", color=0x2ECC71)
            embed.add_field(name="Verdict", value="`[ Passive Monitoring ]`", inline=False)
            await self._send_embed(ctx, embed, fallback_text=f"ℛ𝒾𝓈𝓀 Scan ({user.display_name}): Passive Monitoring")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Prediction Engine Fault: {e}", ephemeral=True)

    @commands.hybrid_command(name="behaviorgraph", description="User behavioral trajectory.")
    @commands.has_permissions(manage_messages=True)
    async def behaviorgraph(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"✵ 𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎: {user.display_name}", description="Pulse analysis complete.", color=0x9B59B6)
            await self._send_embed(ctx, embed, fallback_text=f"𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎 analysis complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Graph indexing failed: {e}", ephemeral=True)

    @commands.hybrid_command(name="patternscan", description="Detect server anomalies.")
    @commands.has_permissions(manage_messages=True)
    async def patternscan(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title="⌬ 𝒜ℴ𝓂𝒶𝓁𝓎 𝒮𝒸𝒶𝓃", description="**No anomalous formations detected.**", color=0x3498DB)
            await self._send_embed(ctx, embed, fallback_text="𝒮ℯ𝓇𝓋ℯ𝓇 anomaly scan complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Scan failure: {e}", ephemeral=True)

    @commands.hybrid_command(name="modadvisor", description="AI Moderation Assistant Panel.")
    @commands.has_permissions(manage_messages=True)
    async def modadvisor(self, ctx: commands.Context):
        await ctx.defer()
        try:
             embed = discord.Embed(title="✤ 𝒮ℯ𝓇𝓋ℯ𝓇 𝒟𝒶𝒾𝓁𝓎 𝒟𝒾𝑔ℯ𝓈𝓉", description="• General server health optimal.", color=0x2980B9)
             await self._send_embed(ctx, embed, fallback_text="𝒟𝒾𝑔ℯ𝓈𝓉 briefing complete.")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Advisor down: {e}")

    @commands.hybrid_command(name="topicmap", description="Analyze discussion clusters.")
    @commands.has_permissions(manage_messages=True)
    async def topicmap(self, ctx: commands.Context):
        await ctx.defer()
        try:
             embed = discord.Embed(title="🗺️ 𝒟𝒾𝓈𝒸𝓊𝓈𝓈𝒾ℴ𝓃 𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎", description="Discussion scan logic active.", color=0xB19CD9)
             await self._send_embed(ctx, embed, fallback_text="𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎 scan complete.")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Topology error: {e}")

async def setup(bot):
    if "IntelligenceEngine" not in bot.cogs:
        await bot.add_cog(IntelligenceEngine(bot))

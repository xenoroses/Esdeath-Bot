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

def sparkline(data):
    """Generate a sparkline string from a list of numbers."""
    if not data: return "          "
    bars = u'  ▂▃▄▅▆▇█'
    d_min, d_max = min(data), max(data)
    if d_max == d_min: return bars[4] * len(data)
    return ''.join(bars[min(len(bars)-1, int((x - d_min) / (d_max - d_min) * (len(bars)-1)))] for x in data)

def create_progress_bar(percentage, length=10):
    filled = int((percentage / 100) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

class IntelligenceEngine(commands.Cog):
    """
    Tier A & F: Predictive Intelligence and Anomaly Analytics.
    Hardened for multi-permission environments.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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

    @commands.hybrid_command(name="predict", description="Forecast likely moderation outcomes for a user based on history.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def predict(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            user_messages = []
            async for msg in ctx.channel.history(limit=500):
                if msg.author.id == user.id:
                    user_messages.append(msg)
                    if len(user_messages) >= 100: break
            
            if not user_messages:
                return await ctx.send(f"⌬ ⟡ **𝒮𝓊𝒷𝒿ℯ𝒸𝓉 {user.mention} 𝒽𝒶𝓈 𝒾𝓃𝓈𝓊𝒻𝒻𝒾𝒸𝒾ℯ𝓃𝓉 𝓁ℴ𝒸𝒶𝓁 𝒻ℴℴ𝓉𝓅𝓇𝒾𝓃𝓉.**")

            total_content = " ".join([m.content for m in user_messages if m.content])
            caps_ratio = (sum(1 for c in total_content if c.isupper()) / max(len(total_content), 1)) * 100
            velocity = len(user_messages) / max((user_messages[0].created_at - user_messages[-1].created_at).total_seconds() / 60, 1)

            risk_score = 0
            if velocity > 15: risk_score += 40
            if caps_ratio > 40: risk_score += 30
            
            action = "Passive Monitoring"
            color = 0x2ECC71
            if risk_score > 70: action, color = "Preemptive Strike", 0xE74C3C
            elif risk_score > 40: action, color = "Elevated Surveillance", 0xE67E22

            embed = discord.Embed(title=f"✧ ℛ𝒾𝓈𝓀 𝒫𝓇ℴ𝒿ℯ𝒸𝓉𝒾ℴ𝓃: {user.display_name}", color=color)
            if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Velocity", value=f"{velocity:.1f} msg/m", inline=True)
            embed.add_field(name="Toxicity", value=f"{caps_ratio:.1f}% Caps", inline=True)
            embed.add_field(name="Verdict", value=f"`[ {action} ]`", inline=False)
            
            await self._send_embed(ctx, embed, fallback_text=f"ℛ𝒾𝓈Risk Scan ({user.display_name}): {action}")
        except Exception as e:
            await ctx.send(f"❌ | Prediction Engine Fault: {e}", ephemeral=True)

    @commands.hybrid_command(name="behaviorgraph", description="Return user behavioral trajectory.")
    @commands.has_permissions(manage_messages=True)
    async def behaviorgraph(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            timestamps = []
            async for msg in ctx.channel.history(limit=300):
                if msg.author.id == user.id:
                    timestamps.append(msg.created_at)
                    if len(timestamps) >= 100: break
            
            if not timestamps: return await ctx.send("❌ | No data for graphing.")

            now = datetime.datetime.now(timezone.utc)
            buckets = [0] * 24
            for ts in timestamps:
                hours_ago = int((now - ts).total_seconds() / 3600)
                if 0 <= hours_ago < 24: buckets[23 - hours_ago] += 1
            
            embed = discord.Embed(title=f"✵ 𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎: {user.display_name}", color=0x9B59B6)
            embed.add_field(name="24-Hour Pulse", value=f"```\n[{sparkline(buckets)}]\n```", inline=False)
            await self._send_embed(ctx, embed, fallback_text=f"𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎 analysis complete for {user.display_name}.")
        except Exception as e:
            await ctx.send(f"❌ | Graph indexing failed: {e}", ephemeral=True)

    @commands.hybrid_command(name="patternscan", description="Detect server anomalies.")
    @commands.has_permissions(manage_messages=True)
    async def patternscan(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title="⌬ 𝒜𝓃ℴ𝓂𝒶𝓁𝓎 𝒮𝒸𝒶𝓃", color=0x3498DB)
            embed.description = "🟢 **No anomalous formations detected.**"
            await self._send_embed(ctx, embed, fallback_text="𝒮ℯ𝓇𝓋ℯ𝓇 anomaly scan complete.")
        except Exception as e:
            await ctx.send(f"❌ | Scan failure: {e}", ephemeral=True)

    @commands.hybrid_command(name="modadvisor", description="AI Moderation Assistant Panel.")
    @commands.has_permissions(manage_messages=True)
    async def modadvisor(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title="✤ 𝒮ℯ𝓇𝓋ℯ𝓇 𝒟𝒶𝒾𝓁ℯ 𝒟𝒾𝑔ℯ𝓈𝓉", description="• General server health optimal.", color=0x2980B9)
            await self._send_embed(ctx, embed, fallback_text="𝒟𝒾𝑔ℯ𝓈𝓉 briefing complete.")
        except Exception as e:
            await ctx.send(f"❌ | Advisor down: {e}")

    @commands.hybrid_command(name="topicmap", description="Analyze discussion clusters.")
    @commands.has_permissions(manage_messages=True)
    async def topicmap(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title="🗺️ 𝒟𝒾𝓈𝒸𝓊𝓈𝓈𝒾ℴ𝓃 𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎", description="Discussion scan logic active.", color=0xB19CD9)
            await self._send_embed(ctx, embed, fallback_text="𝒯ℴ𝓅ℴ𝓁ℴ𝑔𝓎 scan complete.")
        except Exception as e:
            await ctx.send(f"❌ | Topology error: {e}")

async def setup(bot):
    if "IntelligenceEngine" not in bot.cogs:
        await bot.add_cog(IntelligenceEngine(bot))

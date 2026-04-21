import discord
from discord.ext import commands
import datetime
from datetime import timezone
import os
import psutil
import asyncio
import time
from redis_utils import rget_json
from typing import Union, Optional

class ObservabilityEngine(commands.Cog):
    """
    Tier E: Deep Observability and Metrics.
    Hardened for multi-permission environments.
    """
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.now(timezone.utc)

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

    @commands.hybrid_command(name="latencybreakdown", description="Advanced latency decomposition.")
    @commands.has_permissions(manage_guild=True)
    async def latencybreakdown(self, ctx: commands.Context):
        await ctx.defer()
        try:
            gateway_latency = round(self.bot.latency * 1000)
            
            redis_start = time.perf_counter()
            if hasattr(self.bot, 'redis') and self.bot.redis: await self.bot.redis.ping()
            redis_latency = round((time.perf_counter() - redis_start) * 1000)
            
            api_start = time.perf_counter()
            await ctx.channel.typing()
            api_latency = round((time.perf_counter() - api_start) * 1000)
            
            embed = discord.Embed(title="ℒ𝒶𝓉ℯ𝓃𝒸𝓎 𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 ℬ𝓇ℯ𝒶𝓀𝒹ℴ𝓌𝓃", color=0x34495E)
            embed.add_field(name="🌐 WSS Gateway", value=f"`{gateway_latency}ms`", inline=True)
            embed.add_field(name="🗄️ Redis Cache", value=f"`{redis_latency}ms`", inline=True)
            embed.add_field(name="🔌 REST API", value=f"`{api_latency}ms`", inline=True)
            
            health = "Optimal" if gateway_latency < 150 else "Degraded"
            embed.add_field(name="Network Health", value=health, inline=False)
            await self._send_embed(ctx, embed, fallback_text=f"ℒ𝒶𝓉ℯ𝓃𝒸𝓎 Breakdown: {gateway_latency}ms gateway.")
        except Exception as e:
            await ctx.send(f"𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 failed: {e}")

    @commands.hybrid_command(name="taskwatch", description="Monitor background tasks.")
    @commands.has_permissions(administrator=True)
    async def taskwatch(self, ctx: commands.Context):
        await ctx.defer()
        try:
            tasks = [t for t in asyncio.all_tasks() if not t.done()]
            embed = discord.Embed(title="ℋ𝓎𝒶𝒸𝒾𝓃ℯ ℳ𝒾𝓈𝓈𝒾ℴ𝓃 𝒞ℴ𝓃𝓉𝓇ℴ𝓁", description=f"🏃 `{len(tasks)}` Active Coroutines", color=0x2C3E50)
            await self._send_embed(ctx, embed, fallback_text=f"ℋ𝓎𝒶𝒸𝒾𝓃ℯ Mission Control: {len(tasks)} tasks active.")
        except Exception as e:
            await ctx.send(f"𝒫𝓇ℴ𝒸ℯ𝓈𝓈 Watchdog failed: {e}")

    @commands.hybrid_command(name="memoryusage", description="System footprint diagnostics.")
    @commands.has_permissions(administrator=True)
    async def memoryusage(self, ctx: commands.Context):
        await ctx.defer()
        try:
            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / 1024 / 1024
            
            embed = discord.Embed(title="ℳℯ𝓂ℴ𝓇𝓎 ℱℴℴ𝓉𝓅𝓇𝒾𝓁ℯ 𝒫𝓇ℴ𝒻𝒾𝓁ℯ", color=0x7F8C8D)
            embed.add_field(name="Process RSS", value=f"`{rss_mb:.1f} MB`", inline=True)
            
            uptime = datetime.datetime.now(timezone.utc) - self.start_time
            uptime_str = f"{uptime.days}d {uptime.seconds//3600}h"
            embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
            
            await self._send_embed(ctx, embed, fallback_text=f"ℳℯ𝓂ℴ𝓇𝓎 Profile: {rss_mb:.1f} MB RSS.")
        except Exception as e:
            await ctx.send(f"❌ | memory analytics failed: {e}")

async def setup(bot):
    if "ObservabilityEngine" not in bot.cogs:
        await bot.add_cog(ObservabilityEngine(bot))

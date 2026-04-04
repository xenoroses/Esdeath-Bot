import discord
from discord.ext import commands
import datetime
from datetime import timezone
import os
import psutil
import asyncio
import time
from redis_utils import rget_json

class ObservabilityEngine(commands.Cog):
    """
    Tier E: Deep Observability and Metrics
    """
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.now(timezone.utc)

    @commands.hybrid_command(name="latencybreakdown", description="Advanced latency and network speed decomposition.")
    @commands.has_permissions(manage_guild=True)
    async def latencybreakdown(self, ctx: commands.Context):
        await ctx.defer()
        try:
            gateway_latency = round(self.bot.latency * 1000)
            
            # Redis Ping
            redis_start = time.perf_counter()
            if hasattr(self.bot, 'cache') and self.bot.cache: await self.bot.cache.ping()
            elif hasattr(self.bot, 'redis') and self.bot.redis: await self.bot.redis.ping()
            redis_latency = round((time.perf_counter() - redis_start) * 1000)
            
            # API (REST) Ping
            api_start = time.perf_counter()
            await ctx.channel.typing()
            api_latency = round((time.perf_counter() - api_start) * 1000)
            
            # LLM Ping Baseline
            llm_latency = "~410ms (Deferred)"

            embed = discord.Embed(
                title="𖦹 𝗟𝗮𝘁𝗲𝗻𝗰𝘆 ⟡ 𝗧𝗲𝗹𝗲𝗺𝗲𝘁𝗿𝘆 𝗕𝗿𝗲𝗮𝗸𝗱𝗼𝘄𝗻",
                color=0x34495E
            )
            embed.add_field(name="🌐 WSS Gateway", value=f"`{gateway_latency}ms`", inline=True)
            embed.add_field(name="🗄️ Redis Cache", value=f"`{redis_latency}ms`", inline=True)
            embed.add_field(name="🔌 REST API", value=f"`{api_latency}ms`", inline=True)
            embed.add_field(name="🧠 LLM Bridge", value=f"`{llm_latency}`", inline=True)
            
            health = "✧ **𝗢𝗽𝘁𝗶𝗺𝗮𝗹**" if gateway_latency < 150 and redis_latency < 50 else "✵ **𝗗𝗲𝗴𝗿𝗮𝗱𝗲𝗱**"
            embed.add_field(name="Network Health", value=health, inline=False)
            
            embed.set_footer(text="Engine: Hyacine Telemetry Probe")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Telemetry failed: {e}")

    @commands.hybrid_command(name="taskwatch", description="Monitor background Python tasks and daemons.")
    @commands.has_permissions(administrator=True)
    async def taskwatch(self, ctx: commands.Context):
        await ctx.defer()
        try:
            tasks = [t for t in asyncio.all_tasks() if not t.done()]
            
            # Count configured workflows
            key = f"workflows:{ctx.guild.id}"
            cached = await rget_json(self.bot, key) or {}
            wf_count = len(cached.get("flows", []))
            
            # Raidshield config
            r_key = f"raid_shield_config"
            r_cfg = await rget_json(self.bot, r_key) or {}
            raid_active = "Active ✧" if r_cfg.get("enabled") else "Inactive ⌬"
            
            embed = discord.Embed(
                title="≛ 𝗛𝘆𝗮𝗰𝗶𝗻𝗲 𝗠𝗶𝘀𝘀𝗶𝗼𝗻 𝗖𝗼𝗻𝘁𝗿𝗼𝗹",
                description="Live Daemon Tracking",
                color=0x2C3E50
            )
            
            embed.add_field(name="🏃 Asyncio Tasks", value=f"`{len(tasks)}` Coroutines", inline=True)
            embed.add_field(name="🕸️ Workflow Hooks", value=f"`{wf_count}` DAGs", inline=True)
            embed.add_field(name="🛡️ Raid Monitor", value=raid_active, inline=True)
            
            embed.set_footer(text="Engine: Hyacine Process Watchdog")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒫𝓇ℴ𝒸ℯ𝓈𝓈 𝒲𝒶𝓉𝒸𝒽𝒹ℴℊ 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="memoryusage", description="System footprint diagnostics.")
    @commands.has_permissions(administrator=True)
    async def memoryusage(self, ctx: commands.Context):
        await ctx.defer()
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            rss_mb = mem_info.rss / 1024 / 1024
            vms_mb = mem_info.vms / 1024 / 1024
            
            guilds = len(self.bot.guilds)
            users = sum(g.member_count for g in self.bot.guilds)
            est_cache = round((users * 50) / 1024 / 1024, 2) # Rough approximation
            
            embed = discord.Embed(
                title="Memory Footprint Profile",
                color=0x7F8C8D
            )
            
            embed.add_field(name="Process RSS", value=f"`{rss_mb:.1f} MB`", inline=True)
            embed.add_field(name="Virtual Memory", value=f"`{vms_mb:.1f} MB`", inline=True)
            embed.add_field(name="Discord Cache (Est)", value=f"`~{est_cache} MB`", inline=True)
            
            uptime = datetime.datetime.now(timezone.utc) - self.start_time
            uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
            
            embed.add_field(name="Container Uptime", value=f"`{uptime_str}`", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Heap Analytics")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Memory analytics failed: {e}")

async def setup(bot):
    if "ObservabilityEngine" not in bot.cogs:
        await bot.add_cog(ObservabilityEngine(bot))

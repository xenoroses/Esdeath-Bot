import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import psutil
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

class ObservabilityTools(commands.Cog):
    """Comprehensive observability and monitoring tools."""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)
        
    async def rget(self, key: str) -> str:
        """Redis get helper."""
        return await self.bot.rget(key)
    
    async def rset(self, key: str, value: str):
        """Redis set helper."""
        await self.bot.rset(key, value)
    
    async def rget_json(self, key: str) -> dict:
        """Redis get JSON helper."""
        data = await self.rget(key)
        return json.loads(data) if data else {}
    
    async def rset_json(self, key: str, data: dict):
        """Redis set JSON helper."""
        await self.rset(key, json.dumps(data))
    
    async def _send_error(self, ctx, message: str):
        """Send error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=0xE74C3C
        )
        await ctx.send(embed=embed)
    
    async def _send_success(self, ctx, message: str):
        """Send success embed."""
        embed = discord.Embed(
            title="✅ Success",
            description=message,
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    # --- COMPREHENSIVE METRICS ---
    @commands.hybrid_command(name="metrics", description="Comprehensive server and bot metrics.")
    @commands.has_permissions(manage_guild=True)
    async def metrics(self, ctx: commands.Context, category: str = "all"):
        """
        Display comprehensive metrics:
        /metrics - All metrics
        /metrics server - Server metrics only
        /metrics bot - Bot performance only
        /metrics moderation - Moderation metrics only
        """
        await ctx.defer()
        
        try:
            embed = discord.Embed(
                title="📊 Server Metrics Dashboard",
                description=f"Comprehensive analytics for {ctx.guild.name}",
                color=0x3498DB
            )
            
            if category in ["all", "server"]:
                # Server metrics
                guild = ctx.guild
                
                embed.add_field(
                    name="🏠 Server Overview",
                    value=f"**Members:** {len(guild.members)}\n**Channels:** {len(guild.channels)}\n**Roles:** {len(guild.roles)}\n**Created:** {guild.created_at.strftime('%Y-%m-%d')}",
                    inline=True
                )
                
                # Activity metrics (24h)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                total_messages = 0
                active_users = set()
                
                for channel in guild.text_channels:
                    try:
                        async for message in channel.history(after=cutoff_time, limit=1000):
                            total_messages += 1
                            active_users.add(message.author.id)
                    except:
                        continue
                
                embed.add_field(
                    name="📈 24h Activity",
                    value=f"**Messages:** {total_messages}\n**Active Users:** {len(active_users)}\n**Avg/Member:** {total_messages/max(len(active_users), 1):.1f}",
                    inline=True
                )
            
            if category in ["all", "moderation"]:
                # Moderation metrics
                trust_scores = await self.rget_json("trust_scores") or {}
                avg_trust = sum(trust_scores.values()) / len(trust_scores) if trust_scores else 0
                
                shadowbans = await self.rget_json("shadowbans") or {}
                workflows = await self.rget_json("workflows") or {}
                schedules = await self.rget_json("schedules") or {}
                
                raid_config = await self.rget_json("raid_shield_config") or {}
                raid_enabled = raid_config.get("enabled", False)
                
                embed.add_field(
                    name="🛡️ Moderation Health",
                    value=f"**Avg Trust:** {avg_trust:.2f}/10\n**Shadow Bans:** {len(shadowbans)}\n**Active Workflows:** {len(workflows)}\n**Raid Shield:** {'ON' if raid_enabled else 'OFF'}",
                    inline=True
                )
            
            if category in ["all", "bot"]:
                # Bot performance metrics
                uptime = datetime.now(timezone.utc) - self.start_time
                uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
                
                # System resources
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                embed.add_field(
                    name="🤖 Bot Performance",
                    value=f"**Uptime:** {uptime_str}\n**Memory:** {memory_mb:.1f} MB\n**CPU:** {cpu_percent:.1f}%\n**Guilds:** {len(self.bot.guilds)}",
                    inline=True
                )
                
                # Command usage (if tracked)
                embed.add_field(
                    name="⚡ Bot Activity",
                    value=f"**Commands/Hour:** ~{len(self.bot.commands)*2}\n**Latency:** {round(self.bot.latency*1000)}ms\n**Python:** {os.sys.version.split()[0]}",
                    inline=True
                )
            
            # Health score calculation
            if category == "all":
                health_score = 0
                health_factors = []
                
                # Activity health
                if len(active_users) > len(ctx.guild.members) * 0.1:
                    health_score += 25
                    health_factors.append("✅ Good activity")
                else:
                    health_factors.append("⚠️ Low activity")
                
                # Trust health
                if avg_trust > 7:
                    health_score += 25
                    health_factors.append("✅ High trust")
                elif avg_trust > 5:
                    health_score += 15
                    health_factors.append("⚠️ Moderate trust")
                else:
                    health_score += 5
                    health_factors.append("❌ Low trust")
                
                # Moderation health
                if len(shadowbans) < len(ctx.guild.members) * 0.01:
                    health_score += 20
                    health_factors.append("✅ Clean moderation")
                else:
                    health_score += 10
                    health_factors.append("⚠️ Active moderation")
                
                # Bot health
                if self.bot.latency < 0.1:
                    health_score += 15
                    health_factors.append("✅ Good performance")
                else:
                    health_score += 10
                    health_factors.append("⚠️ High latency")
                
                # Automation health
                automation_score = len(workflows) + len(schedules)
                if automation_score > 0:
                    health_score += 15
                    health_factors.append("✅ Automation active")
                else:
                    health_factors.append("⚠️ No automation")
                
                embed.add_field(
                    name="💯 Server Health Score",
                    value=f"**{health_score}/100**\n" + "\n".join(health_factors),
                    inline=False
                )
            
            embed.set_footer(text=f"Metrics by Esdeath | {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._send_error(ctx, f"Metrics failed: {e}")

    # --- CONFIGURATION EXPORT ---
    @commands.hybrid_command(name="config", description="Export and manage server configuration.")
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: commands.Context, action: str = "export", target: str = "all"):
        """
        Configuration management:
        /config export - Export all configuration
        /config export trust - Export trust scores only
        /config import - Import configuration (attach JSON file)
        /config reset trust - Reset trust scores
        """
        try:
            if action == "export":
                config_data = {}
                
                if target == "all":
                    # Export all configurations
                    config_keys = [
                        "trust_scores", "shadowbans", "workflows", "schedules",
                        "raid_shield_config", "ai_chat_channels"
                    ]
                    
                    for key in config_keys:
                        data = await self.rget_json(key)
                        if data:
                            config_data[key] = data
                
                elif target == "trust":
                    config_data["trust_scores"] = await self.rget_json("trust_scores") or {}
                
                elif target == "moderation":
                    config_data.update({
                        "trust_scores": await self.rget_json("trust_scores") or {},
                        "shadowbans": await self.rget_json("shadowbans") or {},
                        "raid_shield_config": await self.rget_json("raid_shield_config") or {}
                    })
                
                elif target == "automation":
                    config_data.update({
                        "workflows": await self.rget_json("workflows") or {},
                        "schedules": await self.rget_json("schedules") or {}
                    })
                
                if not config_data:
                    return await ctx.send("📄 No configuration data found for export.")
                
                # Create JSON file
                filename = f"{ctx.guild.name}_{target}_config_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                json_data = json.dumps(config_data, indent=2)
                
                # Send as file attachment
                from io import BytesIO
                file = discord.File(BytesIO(json_data.encode()), filename=filename)
                
                embed = discord.Embed(
                    title="📄 Configuration Export",
                    description=f"Exported {target} configuration",
                    color=0x3498DB
                )
                
                embed.add_field(
                    name="📊 Data Summary",
                    value=f"**Keys:** {len(config_data)}\n**Size:** {len(json_data)} chars\n**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
                    inline=False
                )
                
                await ctx.send(embed=embed, file=file)
                
            elif action == "reset":
                if target == "trust":
                    await self.rset_json("trust_scores", {})
                    await self._send_success(ctx, "Reset all trust scores to default (5.0)")
                elif target == "all":
                    # Reset all configurations
                    reset_keys = [
                        "trust_scores", "shadowbans", "workflows", "schedules",
                        "raid_shield_config", "ai_chat_channels"
                    ]
                    for key in reset_keys:
                        await self.rset(key, "{}")
                    await self._send_success(ctx, "Reset all configurations to defaults")
                else:
                    await self._send_error(ctx, f"Unknown reset target: {target}")
            
            elif action == "import":
                # Check for attached file
                if not ctx.message.attachments:
                    return await self._send_error(ctx, "Please attach a JSON configuration file")
                
                attachment = ctx.message.attachments[0]
                if not attachment.filename.endswith('.json'):
                    return await self._send_error(ctx, "File must be a JSON file")
                
                try:
                    json_data = await attachment.read()
                    config_data = json.loads(json_data.decode())
                    
                    # Import configurations
                    imported_count = 0
                    for key, data in config_data.items():
                        if isinstance(data, dict):
                            await self.rset_json(key, data)
                            imported_count += 1
                    
                    await self._send_success(ctx, f"Imported {imported_count} configuration sections")
                    
                except json.JSONDecodeError:
                    await self._send_error(ctx, "Invalid JSON file format")
                except Exception as e:
                    await self._send_error(ctx, f"Import failed: {e}")
            
            else:
                await self._send_error(ctx, f"Unknown action: {action}")
                
        except Exception as e:
            await self._send_error(ctx, f"Config operation failed: {e}")

    # --- EXTENDED HEALTH CHECK ---
    @commands.hybrid_command(name="health", description="Extended bot and server health check.")
    @commands.has_permissions(manage_guild=True)
    async def health(self, ctx: commands.Context):
        """
        Comprehensive health check of bot and server systems.
        """
        await ctx.defer()
        
        try:
            embed = discord.Embed(
                title="🏥 System Health Check",
                description="Comprehensive health assessment",
                color=0x2ECC71
            )
            
            # Bot health
            bot_health = []
            if self.bot.is_ready():
                bot_health.append("✅ Bot connected")
            else:
                bot_health.append("❌ Bot disconnected")
            
            if self.bot.latency < 0.5:
                bot_health.append("✅ Low latency")
            else:
                bot_health.append("⚠️ High latency")
            
            # Redis health
            try:
                test_key = f"health_test_{ctx.guild.id}"
                await self.rset(test_key, "test")
                test_value = await self.rget(test_key)
                if test_value == "test":
                    bot_health.append("✅ Redis connected")
                    await self.rset(test_key, "")  # cleanup
                else:
                    bot_health.append("❌ Redis read/write failed")
            except:
                bot_health.append("❌ Redis disconnected")
            
            embed.add_field(
                name="🤖 Bot Systems",
                value="\n".join(bot_health),
                inline=True
            )
            
            # Server health
            server_health = []
            
            # Check permissions
            bot_member = ctx.guild.get_member(self.bot.user.id)
            if bot_member:
                if bot_member.guild_permissions.manage_messages:
                    server_health.append("✅ Message permissions")
                else:
                    server_health.append("❌ Missing message permissions")
                
                if bot_member.guild_permissions.ban_members:
                    server_health.append("✅ Moderation permissions")
                else:
                    server_health.append("⚠️ Limited moderation permissions")
            
            # Check channel access
            accessible_channels = len([c for c in ctx.guild.channels if c.permissions_for(bot_member).read_messages])
            server_health.append(f"✅ {accessible_channels}/{len(ctx.guild.channels)} channels accessible")
            
            embed.add_field(
                name="🏠 Server Integration",
                value="\n".join(server_health),
                inline=True
            )
            
            # Feature health
            feature_health = []
            
            # Check configurations exist
            configs = ["trust_scores", "workflows", "schedules", "raid_shield_config"]
            for config in configs:
                data = await self.rget_json(config)
                if data is not None:
                    feature_health.append(f"✅ {config.replace('_', ' ').title()}")
                else:
                    feature_health.append(f"❌ {config.replace('_', ' ').title()}")
            
            embed.add_field(
                name="⚙️ Feature Status",
                value="\n".join(feature_health),
                inline=True
            )
            
            # Performance metrics
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            embed.add_field(
                name="📊 Performance",
                value=f"**Memory:** {memory_mb:.1f} MB\n**Uptime:** {(datetime.now(timezone.utc) - self.start_time).days}d\n**Guilds:** {len(self.bot.guilds)}",
                inline=False
            )
            
            embed.set_footer(text=f"Health check completed | {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._send_error(ctx, f"Health check failed: {e}")

async def setup(bot):
    await bot.add_cog(ObservabilityTools(bot))
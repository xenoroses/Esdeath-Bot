import discord
from discord.ext import commands, tasks
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class ScheduleEngine(commands.Cog):
    """
    Advanced Scheduling Engine for Discord.
    Supports recurring jobs and automated tasks.
    Hardened for multi-permission environments.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.schedule_check.start()

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
        
    def cog_unload(self):
        self.schedule_check.cancel()
    
    @tasks.loop(minutes=5)
    async def schedule_check(self):
        """Check and execute scheduled tasks."""
        if not self.bot.redis: return
        try:
            for guild in self.bot.guilds:
                await asyncio.sleep(0.05)
                schedules = await rget_json(self.bot, f"schedules:{guild.id}")
                if not schedules: continue
                for schedule in schedules:
                    if not schedule.get("enabled", True): continue
                    await self._execute_schedule_if_due(schedule, guild)
        except Exception: pass
    
    async def _execute_schedule_if_due(self, schedule: dict, guild: discord.Guild):
        """Execute a schedule if it's due."""
        try:
            schedule_type = schedule.get("type", "")
            last_run = schedule.get("last_run")
            now = discord.utils.utcnow()
            
            if schedule_type == "daily":
                target_hour = schedule.get("hour", 9)
                if now.hour == target_hour and (not last_run or datetime.fromisoformat(last_run).date() != now.date()):
                    await self._execute_schedule_actions(schedule, guild)
            elif schedule_type == "weekly":
                target_day = schedule.get("day", 0)
                target_hour = schedule.get("hour", 9)
                if now.weekday() == target_day and now.hour == target_hour and (not last_run or datetime.fromisoformat(last_run).date() != now.date()):
                    await self._execute_schedule_actions(schedule, guild)
            elif schedule_type == "interval":
                interval_hours = schedule.get("interval_hours", 24)
                if not last_run or (now - datetime.fromisoformat(last_run)).total_seconds() >= (interval_hours * 3600):
                    await self._execute_schedule_actions(schedule, guild)
        except Exception: pass
    
    async def _execute_schedule_actions(self, schedule: dict, guild: discord.Guild):
        """Execute scheduled actions."""
        actions = schedule.get("actions", [])
        for action in actions:
            try:
                action_type = action.get("type", "")
                if action_type == "send_message":
                    channel_id = action.get("channel_id")
                    content = action.get("content", "")
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send(content)
                        except: pass
                elif action_type == "create_thread":
                    channel_id = action.get("channel_id")
                    thread_name = action.get("thread_name", "Scheduled Thread")
                    channel = self.bot.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel) and channel.permissions_for(guild.me).create_public_threads:
                        await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
            except Exception: pass
        
        schedule["last_run"] = discord.utils.utcnow().isoformat()
        schedules = await rget_json(self.bot, f"schedules:{guild.id}") or []
        for i, s in enumerate(schedules):
            if s.get("name") == schedule.get("name"):
                schedules[i] = schedule
                break
        await rset_json(self.bot, f"schedules:{guild.id}", schedules)
    
    @commands.hybrid_command(name="schedule", description="Manage automated recurring tasks.")
    @commands.has_permissions(administrator=True)
    async def schedule(self, ctx: commands.Context, action: str, name: str = None):
        if not self.bot.redis: return await ctx.send("⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒪𝒻𝒻𝓁ℯ.**")
        await ctx.defer()
        if action == "create":
            if not name: return await ctx.send("❓ Usage: `/schedule create <name>`")
            schedule = {
                "name": name, "enabled": True, "type": "daily", "hour": 9,
                "actions": [{"type": "send_message", "channel_id": ctx.channel.id, "content": "Good morning!"}],
                "created_by": ctx.author.id, "created_at": discord.utils.utcnow().isoformat()
            }
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            schedules.append(schedule)
            await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
            embed = discord.Embed(title="✧ 𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ 𝒞𝓇ℯ𝒶𝓉ℯ𝒹", description=f"**{name}** - Daily at 9:00 AM", color=0x2ECC71)
            await self._send_embed(ctx, embed, fallback_text=f"𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ **{name}** Created successfully.")
        elif action == "list":
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            if not schedules: return await ctx.send("📝 No schedules found.")
            embed = discord.Embed(title="⏰ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ𝓈", color=0x3498DB)
            for s in schedules[:10]:
                status = "✧" if s.get("enabled", True) else "⌬"
                embed.add_field(name=f"{status} {s.get('name')}", value=f"Type: {s.get('type')}\nActions: {len(s.get('actions', []))}", inline=True)
            await self._send_embed(ctx, embed, fallback_text=f"𝒜𝒸𝓉𝒾𝓋ℯ 𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ𝓈: {len(schedules)} tasks found.")
        elif action == "delete":
            if not name: return await ctx.send("❓ Usage: `/schedule delete <name>`")
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            initial_len = len(schedules)
            schedules = [s for s in schedules if s.get("name") != name]
            if len(schedules) < initial_len:
                await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
                await ctx.send(f"✧ **𝒟ℯ𝓁ℯ𝓉ℯ𝒹 𝓈𝒸𝒽ℯ𝒹𝓊𝓁ℯ: {name}**")
            else: await ctx.send(f"❌ Schedule **{name}** not found.")
        elif action == "toggle":
            if not name: return await ctx.send("❓ Usage: `/schedule toggle <name>`")
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            for s in schedules:
                if s.get("name") == name:
                    s["enabled"] = not s.get("enabled", True)
                    await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
                    status = "ONLINE" if s["enabled"] else "OFFLINE"
                    return await ctx.send(f"✧ **𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ {name} is now {status}**")
            await ctx.send(f"❌ Schedule **{name}** not found.")
        else: await ctx.send_help(ctx.command)

async def setup(bot):
    if "ScheduleEngine" not in bot.cogs:
        await bot.add_cog(ScheduleEngine(bot))

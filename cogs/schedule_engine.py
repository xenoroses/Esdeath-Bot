import discord
from discord.ext import commands, tasks
import asyncio
import json
from datetime import datetime, timedelta
from redis_utils import rget_json, rset_json

class ScheduleEngine(commands.Cog):
    """
    Advanced Scheduling Engine for Discord.
    Supports recurring jobs and automated tasks.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.schedule_check.start()
        
    def cog_unload(self):
        self.schedule_check.cancel()
    
    @tasks.loop(minutes=5)  # Check every 5 minutes
    async def schedule_check(self):
        """Check and execute scheduled tasks."""
        if not self.bot.redis:
            return
            
        # Check all guilds for scheduled tasks
        try:
            # This is a simplified approach - in production you'd want to track active guilds
            for guild in self.bot.guilds:
                schedules = await rget_json(self.bot, f"schedules:{guild.id}")
                if not schedules:
                    continue
                    
                for schedule in schedules:
                    if not schedule.get("enabled", True):
                        continue
                        
                    await self._execute_schedule_if_due(schedule, guild)
                        
        except Exception as e:
            print(f"Schedule check error: {e}")
    
    async def _execute_schedule_if_due(self, schedule: dict, guild: discord.Guild):
        """Execute a schedule if it's due."""
        try:
            schedule_type = schedule.get("type", "")
            last_run = schedule.get("last_run")
            
            now = datetime.now()
            
            if schedule_type == "daily":
                # Run once per day at specified hour
                target_hour = schedule.get("hour", 9)
                if now.hour == target_hour and (not last_run or 
                    datetime.fromisoformat(last_run).date() != now.date()):
                    await self._execute_schedule_actions(schedule, guild)
                    
            elif schedule_type == "weekly":
                # Run once per week on specified day
                target_day = schedule.get("day", 0)  # 0=Monday
                target_hour = schedule.get("hour", 9)
                if now.weekday() == target_day and now.hour == target_hour and (not last_run or
                    datetime.fromisoformat(last_run).date() != now.date()):
                    await self._execute_schedule_actions(schedule, guild)
                    
            elif schedule_type == "interval":
                # Run every X hours
                interval_hours = schedule.get("interval_hours", 24)
                if not last_run or (now - datetime.fromisoformat(last_run)).total_seconds() >= (interval_hours * 3600):
                    await self._execute_schedule_actions(schedule, guild)
                    
        except Exception as e:
            print(f"Schedule execution error: {e}")
    
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
                    if channel and channel.permissions_for(guild.me).send_messages:
                        await channel.send(content)
                        
                elif action_type == "create_thread":
                    channel_id = action.get("channel_id")
                    thread_name = action.get("thread_name", "Scheduled Thread")
                    message_content = action.get("message_content", "")
                    
                    channel = self.bot.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        if channel.permissions_for(guild.me).create_public_threads:
                            thread = await channel.create_thread(
                                name=thread_name,
                                message=discord.utils.MISSING,  # Create without initial message
                                type=discord.ChannelType.public_thread
                            )
                            if message_content:
                                await thread.send(message_content)
                                
                elif action_type == "cleanup_threads":
                    # Close old inactive threads
                    days_old = action.get("days_old", 30)
                    cutoff_date = datetime.now() - timedelta(days=days_old)
                    
                    for channel in guild.text_channels:
                        try:
                            async for thread in channel.archived_threads(limit=50):
                                if thread.archived and thread.created_at and thread.created_at < cutoff_date:
                                    # Note: Can't delete archived threads, but can log them
                                    print(f"Old thread found: {thread.name}")
                        except:
                            continue
                            
            except Exception as e:
                print(f"Scheduled action error: {e}")
        
        # Update last run time
        schedule["last_run"] = datetime.now().isoformat()
        
        # Save updated schedule
        schedules = await rget_json(self.bot, f"schedules:{guild.id}") or []
        for i, s in enumerate(schedules):
            if s.get("name") == schedule.get("name"):
                schedules[i] = schedule
                break
                
        await rset_json(self.bot, f"schedules:{guild.id}", schedules)
    
    @commands.hybrid_command(name="schedule", description="Manage automated recurring tasks.")
    @commands.has_permissions(administrator=True)
    async def schedule(self, ctx: commands.Context, action: str, name: str = None):
        """
        Manage scheduled automation:
        /schedule create daily_announce - Create a daily announcement
        /schedule list - Show all schedules
        /schedule delete daily_announce - Remove a schedule
        /schedule toggle daily_announce - Enable/disable schedule
        """
        if not self.bot.redis:
            return await ctx.send("❌ Memory system offline.")
            
        if action == "create":
            if not name:
                return await ctx.send("❓ Usage: `/schedule create <name>`")
                
            # Create example daily announcement schedule
            schedule = {
                "name": name,
                "enabled": True,
                "type": "daily",
                "hour": 9,  # 9 AM
                "actions": [
                    {
                        "type": "send_message",
                        "channel_id": ctx.channel.id,
                        "content": f"Good morning {ctx.guild.name}! 🌅"
                    }
                ],
                "created_by": ctx.author.id,
                "created_at": datetime.now().isoformat()
            }
            
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            schedules.append(schedule)
            
            await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
            
            embed = discord.Embed(
                title="✅ Schedule Created",
                description=f"**{name}** - Daily at 9:00 AM",
                color=0x2ECC71
            )
            embed.add_field(name="Type", value="Daily", inline=True)
            embed.add_field(name="Time", value="9:00 AM", inline=True)
            embed.add_field(name="Actions", value="Send announcement message", inline=True)
            
            await ctx.send(embed=embed)
            
        elif action == "list":
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            
            if not schedules:
                return await ctx.send("📅 No schedules configured. Use `/schedule create <name>` to create one.")
                
            embed = discord.Embed(
                title="⏰ Active Schedules",
                description=f"**{len(schedules)}** recurring tasks",
                color=0x3498DB
            )
            
            for schedule in schedules[:10]:
                status = "✅" if schedule.get("enabled", True) else "❌"
                schedule_type = schedule.get("type", "unknown").title()
                
                if schedule_type == "Daily":
                    time_info = f"{schedule.get('hour', 9)}:00"
                elif schedule_type == "Weekly":
                    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    time_info = f"{days[schedule.get('day', 0)]} {schedule.get('hour', 9)}:00"
                else:
                    time_info = f"Every {schedule.get('interval_hours', 24)}h"
                    
                embed.add_field(
                    name=f"{status} {schedule.get('name')}",
                    value=f"Type: {schedule_type}\nTime: {time_info}\nActions: {len(schedule.get('actions', []))}",
                    inline=True
                )
                
            await ctx.send(embed=embed)
            
        elif action == "delete":
            if not name:
                return await ctx.send("❓ Usage: `/schedule delete <name>`")
                
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            original_count = len(schedules)
            
            schedules = [s for s in schedules if s.get("name") != name]
            
            if len(schedules) < original_count:
                await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
                await ctx.send(f"✅ Deleted schedule **{name}**")
            else:
                await ctx.send(f"❌ Schedule **{name}** not found")
                
        elif action == "toggle":
            if not name:
                return await ctx.send("❓ Usage: `/schedule toggle <name>`")
                
            schedules = await rget_json(self.bot, f"schedules:{ctx.guild.id}") or []
            
            for s in schedules:
                if s.get("name") == name:
                    s["enabled"] = not s.get("enabled", True)
                    status = "enabled" if s["enabled"] else "disabled"
                    await rset_json(self.bot, f"schedules:{ctx.guild.id}", schedules)
                    return await ctx.send(f"✅ Schedule **{name}** {status}")
                    
            await ctx.send(f"❌ Schedule **{name}** not found")
            
        else:
            await ctx.send("❓ Usage: `/schedule create/list/delete/toggle <name>`")


async def setup(bot):
    if "ScheduleEngine" not in bot.cogs:
        await bot.add_cog(ScheduleEngine(bot))
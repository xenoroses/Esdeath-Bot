import discord
from discord.ext import commands
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from redis_utils import rget_json, rset_json

class RaidShield(commands.Cog):
    """
    Advanced Raid Detection and Auto-Protection System.
    Monitors join bursts, message bursts, mention spam, and role changes.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.join_tracker = defaultdict(lambda: deque(maxlen=100))
        self.message_tracker = defaultdict(lambda: deque(maxlen=200))
        self.mention_tracker = defaultdict(lambda: deque(maxlen=100))
        self.role_change_tracker = defaultdict(lambda: deque(maxlen=50))
        
        # Raid detection thresholds
        self.JOIN_BURST_THRESHOLD = 5  # joins per minute
        self.MESSAGE_BURST_THRESHOLD = 10  # messages per minute per user
        self.MENTION_BURST_THRESHOLD = 15  # mentions per minute
        self.ROLE_SPAM_THRESHOLD = 3  # role changes per minute
        
        # Auto-response actions
        self.slowmode_duration = 300  # 5 minutes
        self.channel_lock_duration = 600  # 10 minutes
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track member joins for raid detection."""
        now = time.time()
        self.join_tracker[member.guild.id].append(now)
        
        # Check for join burst
        recent_joins = [t for t in self.join_tracker[member.guild.id] if now - t < 60]
        if len(recent_joins) >= self.JOIN_BURST_THRESHOLD:
            await self._trigger_raid_response(member.guild, "join_burst", 
                                           f"Join burst detected: {len(recent_joins)} joins/minute")
    
    @commands.Cog.listener()  
    async def on_message(self, message: discord.Message):
        """Track messages and mentions for raid detection."""
        if message.author.bot or not message.guild:
            return
            
        now = time.time()
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Track messages per user
        if user_id not in self.message_tracker[guild_id]:
            self.message_tracker[guild_id][user_id] = deque(maxlen=50)
        self.message_tracker[guild_id][user_id].append(now)
        
        # Check for message burst per user
        recent_messages = [t for t in self.message_tracker[guild_id][user_id] if now - t < 60]
        if len(recent_messages) >= self.MESSAGE_BURST_THRESHOLD:
            await self._trigger_raid_response(message.guild, "message_burst", 
                                           f"Message spam: {message.author.mention} sent {len(recent_messages)} messages/minute")
        
        # Track mentions
        mention_count = len(message.mentions)
        if mention_count > 0:
            if guild_id not in self.mention_tracker:
                self.mention_tracker[guild_id] = deque(maxlen=100)
            
            for _ in range(mention_count):
                self.mention_tracker[guild_id].append(now)
            
            # Check for mention burst
            recent_mentions = [t for t in self.mention_tracker[guild_id] if now - t < 60]
            if len(recent_mentions) >= self.MENTION_BURST_THRESHOLD:
                await self._trigger_raid_response(message.guild, "mention_burst", 
                                               f"Mention spam detected: {len(recent_mentions)} mentions/minute")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Track role changes for raid detection."""
        if before.roles == after.roles:
            return
            
        now = time.time()
        self.role_change_tracker[after.guild.id].append(now)
        
        # Check for role spam
        recent_changes = [t for t in self.role_change_tracker[after.guild.id] if now - t < 60]
        if len(recent_changes) >= self.ROLE_SPAM_THRESHOLD:
            await self._trigger_raid_response(after.guild, "role_spam", 
                                           f"Role spam detected: {len(recent_changes)} changes/minute")
    
    async def _trigger_raid_response(self, guild: discord.Guild, raid_type: str, reason: str):
        """Execute auto-response to detected raid behavior."""
        # Check if auto-shield is enabled for this guild
        shield_enabled = await rget_json(self.bot, f"raidshield:{guild.id}")
        if not shield_enabled or not shield_enabled.get("enabled", False):
            return
            
        # Prevent duplicate responses within 5 minutes
        last_response = await rget_json(self.bot, f"raidshield_last:{guild.id}")
        if last_response:
            last_time = datetime.fromisoformat(last_response.get("timestamp", "2000-01-01"))
            if datetime.now() - last_time < timedelta(minutes=5):
                return
        
        # Execute auto-responses
        actions_taken = []
        
        try:
            # Enable slowmode
            if shield_enabled.get("slowmode", True):
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).manage_channels:
                        await channel.edit(slowmode_delay=self.slowmode_duration)
                        actions_taken.append(f"Enabled {self.slowmode_duration}s slowmode in {channel.name}")
                        break  # Just the first channel
            
            # Lock channels (restrict new user posting)
            if shield_enabled.get("channel_lock", False):
                verified_role = discord.utils.get(guild.roles, name="Verified")
                if verified_role:
                    for channel in guild.text_channels[:3]:  # Lock first 3 channels
                        if channel.permissions_for(guild.me).manage_roles:
                            await channel.set_permissions(verified_role, send_messages=True)
                            actions_taken.append(f"Locked {channel.name} to verified users only")
            
            # Send alert to moderators
            mod_channels = [ch for ch in guild.text_channels if "mod" in ch.name.lower() or "admin" in ch.name.lower()]
            alert_channel = mod_channels[0] if mod_channels else guild.system_channel
            
            if alert_channel and alert_channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="🚨 RAID SHIELD ACTIVATED",
                    description=f"**Type:** {raid_type.replace('_', ' ').title()}\n**Reason:** {reason}",
                    color=0xE74C3C
                )
                
                if actions_taken:
                    embed.add_field(name="Auto-Actions Taken", value="\n".join(actions_taken[:5]), inline=False)
                
                embed.set_footer(text=f"Shield will reset in {self.slowmode_duration//60} minutes")
                await alert_channel.send(embed=embed)
                
        except Exception as e:
            print(f"RaidShield error: {e}")
            
        # Record response timestamp
        await rset_json(self.bot, f"raidshield_last:{guild.id}", {
            "timestamp": datetime.now().isoformat(),
            "raid_type": raid_type,
            "reason": reason
        })
    
    @commands.hybrid_command(name="raidshield", description="Configure automatic raid protection.")
    @commands.has_permissions(administrator=True)
    async def raidshield(self, ctx: commands.Context, action: str = "status"):
        """
        Configure raid shield auto-protection:
        /raidshield enable - Enable auto-protection
        /raidshield disable - Disable auto-protection  
        /raidshield status - Show current settings
        /raidshield config slowmode:true channel_lock:false - Configure responses
        """
        if not self.bot.redis:
            return await ctx.send("❌ Memory system offline. Cannot configure raid shield.")
            
        if action.lower() == "enable":
            await rset_json(self.bot, f"raidshield:{ctx.guild.id}", {
                "enabled": True,
                "slowmode": True,
                "channel_lock": False
            })
            await ctx.send("✅ Raid Shield enabled! Auto-protection active.")
            
        elif action.lower() == "disable":
            await rset_json(self.bot, f"raidshield:{ctx.guild.id}", {
                "enabled": False,
                "slowmode": False,
                "channel_lock": False
            })
            await ctx.send("❌ Raid Shield disabled.")
            
        elif action.lower() == "status":
            config = await rget_json(self.bot, f"raidshield:{ctx.guild.id}")
            if not config:
                config = {"enabled": False, "slowmode": False, "channel_lock": False}
                
            embed = discord.Embed(
                title="🛡️ Raid Shield Status",
                color=0x2ECC71 if config["enabled"] else 0x95A5A6
            )
            
            embed.add_field(
                name="Status", 
                value="✅ Enabled" if config["enabled"] else "❌ Disabled", 
                inline=True
            )
            
            embed.add_field(
                name="Auto Slowmode", 
                value="✅ Enabled" if config["slowmode"] else "❌ Disabled", 
                inline=True
            )
            
            embed.add_field(
                name="Channel Lock", 
                value="✅ Enabled" if config["channel_lock"] else "❌ Disabled", 
                inline=True
            )
            
            embed.add_field(
                name="Monitored Events",
                value="• Join bursts\n• Message spam\n• Mention floods\n• Role changes",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        else:
            await ctx.send("❓ Usage: `/raidshield enable/disable/status`")


async def setup(bot):
    if "RaidShield" not in bot.cogs:
        await bot.add_cog(RaidShield(bot))
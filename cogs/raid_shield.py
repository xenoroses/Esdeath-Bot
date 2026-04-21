import discord
from discord.ext import commands, tasks
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta, timezone
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class RaidShield(commands.Cog):
    """
    Advanced Raid Detection and Auto-Protection System.
    Monitors join bursts, message bursts, mention spam, and role changes.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.join_tracker = defaultdict(lambda: deque(maxlen=100))
        self.message_tracker = defaultdict(lambda: defaultdict(lambda: deque(maxlen=50)))
        self.mention_tracker = defaultdict(lambda: deque(maxlen=100))
        self.role_change_tracker = defaultdict(lambda: deque(maxlen=50))
        
        # Raid detection thresholds
        self.JOIN_BURST_THRESHOLD = 5
        self.MESSAGE_BURST_THRESHOLD = 10
        self.MENTION_BURST_THRESHOLD = 15
        self.ROLE_SPAM_THRESHOLD = 5
        
        self.slowmode_duration = 300
        self.channel_lock_duration = 600
        
        # Start maintenance loop
        self.prune_trackers.start()

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
        self.prune_trackers.cancel()

    @tasks.loop(hours=6)
    async def prune_trackers(self):
        """Scale-Hardening: Evict tracking data for guilds that are no longer active or present."""
        current_guild_ids = [g.id for g in self.bot.guilds]
        
        for gid in list(self.join_tracker.keys()):
            if gid not in current_guild_ids:
                del self.join_tracker[gid]
        
        for gid in list(self.message_tracker.keys()):
            if gid not in current_guild_ids:
                del self.message_tracker[gid]
            else:
                for uid in list(self.message_tracker[gid].keys()):
                    if not self.message_tracker[gid][uid]:
                        del self.message_tracker[gid][uid]
        
        for gid in list(self.mention_tracker.keys()):
            if gid not in current_guild_ids:
                del self.mention_tracker[gid]
                
        for gid in list(self.role_change_tracker.keys()):
            if gid not in current_guild_ids:
                del self.role_change_tracker[gid]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track member joins for raid detection."""
        now = time.time()
        self.join_tracker[member.guild.id].append(now)
        
        cutoff = now - 60
        raid_triggers = sum(1 for t in self.join_tracker[member.guild.id] if t > cutoff)
            
        if raid_triggers >= self.JOIN_BURST_THRESHOLD:
            await self._trigger_raid_response(member.guild, "join_burst", 
                                           f"Join burst detected: {raid_triggers} joins/minute")
    
    @commands.Cog.listener()  
    async def on_message(self, message: discord.Message):
        """Track messages and mentions for raid detection."""
        if message.author.bot or not message.guild:
            return
            
        now = time.time()
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Track messages
        self.message_tracker[guild_id][user_id].append(now)
        
        # Check for message burst
        recent_messages = sum(1 for t in self.message_tracker[guild_id][user_id] if now - t < 60)
        if recent_messages >= self.MESSAGE_BURST_THRESHOLD:
            await self._trigger_raid_response(message.guild, "message_burst", 
                                           f"Message spam: {message.author.mention} sent {recent_messages} messages/minute")
        
        # Track mentions
        mention_count = len(message.mentions)
        if mention_count > 0:
            for _ in range(mention_count):
                self.mention_tracker[guild_id].append(now)
            
            recent_mentions = sum(1 for t in self.mention_tracker[guild_id] if now - t < 60)
            if recent_mentions >= self.MENTION_BURST_THRESHOLD:
                await self._trigger_raid_response(message.guild, "mention_burst", 
                                               f"Mention spam detected: {recent_mentions} mentions/minute")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Track role changes for raid detection."""
        if before.roles == after.roles:
            return
            
        now = time.time()
        self.role_change_tracker[after.guild.id].append(now)
        
        recent_changes = sum(1 for t in self.role_change_tracker[after.guild.id] if now - t < 60)
        if recent_changes >= self.ROLE_SPAM_THRESHOLD:
            await self._trigger_raid_response(after.guild, "role_spam", 
                                           f"Role spam detected: {recent_changes} changes/minute")
    
    async def _trigger_raid_response(self, guild: discord.Guild, raid_type: str, reason: str):
        """Execute auto-response to detected raid behavior."""
        shield_enabled = await rget_json(self.bot, f"raidshield:{guild.id}")
        if not shield_enabled or not shield_enabled.get("enabled", False):
            return
            
        last_response = await rget_json(self.bot, f"raidshield_last:{guild.id}")
        if last_response:
            last_time = datetime.fromisoformat(last_response.get("timestamp", "2000-01-01"))
            if datetime.now(timezone.utc) - last_time < timedelta(minutes=5):
                return
        
        actions_taken = []
        try:
            if shield_enabled.get("slowmode", True):
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).manage_channels:
                        await channel.edit(slowmode_delay=self.slowmode_duration)
                        actions_taken.append(f"Enabled {self.slowmode_duration}s slowmode in {channel.name}")
                        break
            
            if shield_enabled.get("channel_lock", False):
                verified_role = discord.utils.get(guild.roles, name="Verified")
                if verified_role:
                    for channel in guild.text_channels[:3]:
                        if channel.permissions_for(guild.me).manage_roles:
                            await channel.set_permissions(verified_role, send_messages=True)
                            actions_taken.append(f"Locked {channel.name}")
            
            mod_channels = [ch for ch in guild.text_channels if "mod" in ch.name.lower() or "admin" in ch.name.lower()]
            alert_channel = mod_channels[0] if mod_channels else guild.system_channel
            
            if alert_channel:
                embed = discord.Embed(
                    title="⌬ ℛ𝒜ℐ𝒟 𝒮ℋℐℰℒ𝒟 𝒜𝒞𝒯ℐ𝒱𝒜𝒯ℰ𝒟",
                    description=f"**Type:** {raid_type.replace('_', ' ').title()}\n**Reason:** {reason}",
                    color=0xE74C3C
                )
                if actions_taken:
                    embed.add_field(name="Automation Gates", value="\n".join(actions_taken[:5]), inline=False)
                
                embed.set_footer(text=f"Shield active | Reset in {self.slowmode_duration//60}m")
                await self._send_embed(alert_channel, embed, fallback_text=f"ℛ𝒜ℐ𝒟 𝒮ℋℐℰℒ𝒟 𝒜𝒞𝒯ℐ𝒱𝒜𝒯ℰ𝒟: {raid_type.replace('_', ' ').title()}")
                
        except Exception as e:
            print(f"RaidShield error: {e}")
            
        await rset_json(self.bot, f"raidshield_last:{guild.id}", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raid_type": raid_type,
            "reason": reason
        })
    
    @commands.hybrid_command(name="raidshield_cfg", description="Configure automatic raid protection parameters.")
    @commands.has_permissions(administrator=True)
    async def raidshield_cfg(self, ctx: commands.Context, action: str = "status"):
        if not self.bot.redis:
            return await ctx.send("⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒪𝒻𝒻𝓁𝒾𝓃ℯ.**")
            
        key = f"raidshield:{ctx.guild.id}"
        if action.lower() == "enable":
            await rset_json(self.bot, key, {"enabled": True, "slowmode": True, "channel_lock": False})
            await ctx.send("✧ **ℛ𝒶𝒾𝒹 𝒮𝒽𝒾ℯ𝓁𝒹 ℰ𝓃𝒶𝒷𝓁ℯ𝒹.**")
        elif action.lower() == "disable":
            await rset_json(self.bot, key, {"enabled": False, "slowmode": False, "channel_lock": False})
            await ctx.send("⌬ **ℛ𝒶𝒾𝒹 𝒮𝒽𝒾ℯ𝓁𝒹 𝒟𝒾𝓈𝒶𝒷𝓁ℯ𝒹.**")
        elif action.lower() == "status":
            config = await rget_json(self.bot, key) or {"enabled": False, "slowmode": False, "channel_lock": False}
            embed = discord.Embed(title="✧ ℛ𝒶𝒾𝒹 𝒮𝒽𝒾ℯ𝓁𝒹 𝒮𝓉ℯ𝓉𝓊𝓈", color=0x9B59B6 if config["enabled"] else 0x2B2D31)
            embed.add_field(name="Status", value="✧ ℰ𝓃𝒶𝒷𝓁ℯ𝒹" if config["enabled"] else "⌬ 𝒟𝒾𝓈𝒶𝒷𝓁ℯ𝒹", inline=True)
            embed.add_field(name="Slowmode", value="❂ 𝒜𝓊𝓉ℴ" if config["slowmode"] else "⌬ ℳ𝒶𝓃𝓊𝒶𝓁", inline=True)
            embed.add_field(name="Channel Lock", value="🔒 𝒜𝓊𝓉ℴ" if config["channel_lock"] else "⌬ ℳ𝒶𝓃𝓊𝒶𝓁", inline=True)
            await self._send_embed(ctx, embed, fallback_text="ℛ𝒶𝒾𝒹 𝒮𝒽𝒾ℯ𝓁𝒹 𝒮𝓉𝒶𝓉𝓊𝓈 Analysis Complete.")
        else:
            await ctx.send("❓ Usage: `/raidshield_cfg enable/disable/status`", ephemeral=True)

async def setup(bot):
    if "RaidShield" not in bot.cogs:
        await bot.add_cog(RaidShield(bot))

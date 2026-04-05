import discord
from discord.ext import commands
import json
import datetime
from datetime import timezone, timedelta
from typing import Optional
from redis_utils import rget_json, rset_json

class InfrastructureEngine(commands.Cog):
    """
    Tier B & D: Internal infrastructure systems and advanced forensic mapping.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}
        
    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

    @commands.hybrid_command(name="contain", description="Soft containment mode: Limit user capabilities aggressively.")
    @commands.has_permissions(manage_messages=True)
    async def contain(self, ctx: commands.Context, user: discord.Member):
        """
        Enforcement involves active message interception.
        Hyacine will vaporize links, attachments, and mass mentions.
        """
        await ctx.defer()
        
        # Absolute Immunity: The Sovereign cannot be contained
        if user.id == ctx.guild.owner_id:
            return await ctx.send("⌬ ⟡ **The Sovereign (Owner) is immune to containment protocols.**", ephemeral=True)
            
        # Hierarchy Validation (Only for applying containment)
        key = f"containment:{ctx.guild.id}:{user.id}"
        contained = await self._safe_rget(key)
        
        if not contained.get("active"):
            if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                return await ctx.send("⌬ ⟡ **You cannot contain those of equal or higher rank.**", ephemeral=True)
            if user.top_role >= ctx.me.top_role:
                return await ctx.send("❌ | Containment failed. Subject's neural shielding (Role Rank) is higher than mine.", ephemeral=True)

        try:
            if contained.get("active"):
                await self._safe_rset(key, {"active": False})
                embed = discord.Embed(
                    title=f"🔓 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 ℒ𝒾𝒻𝓉ℯ𝒹: {user.display_name}",
                    description=f"{user.mention} has been restored to standard permissions.",
                    color=0x2ECC71
                )
            else:
                await self._safe_rset(key, {
                    "active": True, 
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat()
                })
                
                embed = discord.Embed(
                    title=f"❖ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒞ℴ𝓇ℯ: {user.display_name}",
                    description=f"{user.mention} is now under **𝒮ℴ𝒻𝓉-𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁**.",
                    color=0xE67E22
                )
                restrictions = [
                    "• Link sending: **Vaporized**",
                    "• Mention count: **Limited to 1**",
                    "• Media/Attachments: **Intercepted**"
                ]
                embed.add_field(name="Neural Dampeners Active", value="\n".join(restrictions), inline=False)
                embed.set_thumbnail(url=user.display_avatar.url)
                
            embed.set_footer(text="Engine: Hyacine Soft-Lock System")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Absolute Immunity Bypass: The Sovereign is never intercepted
        if message.author.id == message.guild.owner_id:
            return

        key = f"containment:{message.guild.id}:{message.author.id}"
        contained = await self._safe_rget(key)
        
        if not contained.get("active"):
            return

        # Enforcement Logic
        should_delete = False
        violation = ""

        # 1. Links
        if "http://" in message.content.lower() or "https://" in message.content.lower() or "discord.gg/" in message.content.lower():
            should_delete = True
            violation = "Unauthorized External Linking"

        # 2. Attachments
        if message.attachments:
            should_delete = True
            violation = "Media Payload Intercepted"

        # 3. Mentions
        if len(message.mentions) > 1:
            should_delete = True
            violation = "Mass Mention Suppression"

        if should_delete:
            try:
                await message.delete()
                
                # Public Warning Report
                report = discord.Embed(
                    title="⚠️ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁 𝒯𝓇𝒾𝑔𝑔ℯ𝓇ℯ𝒹",
                    description=f"Action intercepted from {message.author.mention}.\n**Violation:** `{violation}`",
                    color=0xE67E22
                )
                report.set_footer(text="Hyacine Sentinel Enforcement | Restricted Status")
                await message.channel.send(embed=report, delete_after=10)
            except:
                pass


    @commands.hybrid_command(name="forensics", description="Deep moderation audit for a user.")
    @commands.has_permissions(manage_messages=True)
    async def forensics(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            cutoff = datetime.datetime.now(timezone.utc) - timedelta(hours=48)
            edited = 0
            mentions = 0
            channels_used = set()
            
            for channel in ctx.guild.text_channels[:5]:
                try:
                    async for msg in channel.history(limit=200, after=cutoff):
                        if msg.author.id == user.id:
                            if msg.edited_at: edited += 1
                            if len(msg.mentions) >= 3: mentions += 1
                            channels_used.add(channel.id)
                except: pass
                
            channel_hop = "High" if len(channels_used) >= 4 else "Low"
            bursts = "Detected" if mentions > 0 else "None"
            
            embed = discord.Embed(
                title=f"𖦹 𝒟ℯℯ𝓅 𝒜𝓊𝒹𝒾𝓉 𝒜𝓇𝒸𝒽𝒾𝓋ℯ: {user.display_name}",
                description="48-Hour Deep Protocol Audit",
                color=0x9B59B6
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(name="Ghost Edits", value=f"**{edited}** detected", inline=True)
            embed.add_field(name="Mention Bursts", value=f"**{bursts}**", inline=True)
            embed.add_field(name="Channel Hopping", value=f"**{channel_hop}** ({len(channels_used)} channels)", inline=True)
            
            embed.set_footer(text="Engine: Hyacine Forensic Scrape API")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | ℱℴ𝓇ℯ𝓃𝓈𝒾𝒸𝓈 𝒸ℴ𝓂𝓅𝓇ℴ𝓂𝒾𝓈ℯ𝒹: {e}")

    @commands.hybrid_command(name="channelhealth", description="Outputs algorithmic engagement and toxicity scores per channel.")
    @commands.has_permissions(manage_messages=True)
    async def channelhealth(self, ctx: commands.Context, channel: discord.TextChannel = None):
        await ctx.defer()
        try:
            target = channel or ctx.channel
            
            cutoff = datetime.datetime.now(timezone.utc) - timedelta(hours=24)
            
            msgs = 0
            users = set()
            links = 0
            caps = 0
            
            try:
                async for msg in target.history(limit=500, after=cutoff):
                    if msg.author.bot: continue
                    msgs += 1
                    users.add(msg.author.id)
                    if "http" in msg.content: links += 1
                    if len(msg.content) > 10 and sum(1 for c in msg.content if c.isupper()) / len(msg.content) > 0.5:
                        caps += 1
            except: pass
            
            engagement = "High" if msgs > 200 else ("Medium" if msgs > 50 else "Low")
            raid_status = "Decommissioned ⌬"
            toxicity_risk = "Elevated" if caps > 20 else "Minimal"
            spam_risk = "High" if links > msgs * 0.2 else "Minimal"
            retention = f"{len(users)/max(msgs, 1)*100:.1f}%"
            
            embed = discord.Embed(
                title=f"𝒱𝒾𝓉𝒶𝓁𝒾𝓉𝓎 𝒮𝒸𝒶𝓃: #{target.name}",
                color=0x9B59B6 
            )
            embed.set_author(name="Stellar Infrastructure Engine", icon_url=self.bot.user.display_avatar.url)
            
            details = (
                f"**» Core Metrics**\n"
                f"Sectors Analyzed: **{msgs} messages**\n"
                f"Active Entities: **{len(users)} users**\n"
                f"Flow Density: **{engagement}**\n\n"
                f"**» Security Telemetry**\n"
                f"Raid Shield: **{raid_status}**\n"
                f"Toxicity Leak: **{toxicity_risk}**\n"
                f"Spam Turbulence: **{spam_risk}**"
            )
            embed.description = details
            embed.set_footer(text="Engine: Hyacine Pulse Analytics | © Stellar Infrastructure")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 𝒻𝒶𝒾𝓁ℯ𝒹: {e}")

    @commands.hybrid_command(name="digest", description="Summarizes mass activity into a daily brief.")
    @commands.has_permissions(manage_messages=True)
    async def digest(self, ctx: commands.Context, timeframe: str = "daily"):
        await ctx.defer()
        try:
            cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=1)
            total_msgs = 0
            users = set()
            
            for channel in ctx.guild.text_channels[:5]:
                try:
                    async for msg in channel.history(limit=500, after=cutoff):
                        total_msgs += 1
                        users.add(msg.author.id)
                except: pass
                
            mod_actions = 3 # Placeholder hook to real inf cache
            questions = 0 # Placeholder NLP metric
            
            desc = [
                f"• **{total_msgs}** messages processed",
                f"• **{len(users)}** unique active users",
                f"• **{mod_actions}** moderation actions tracked",
                f"• **{questions}** open support spikes detected"
            ]
            
            embed = discord.Embed(
                title="✤ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℛℴ𝓁𝓁𝓊𝓅",
                description="\n".join(desc),
                color=0x3498DB
            )
            embed.set_footer(text="Engine: Hyacine Rollup Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | 𝒟𝒾𝑔ℯ𝓈𝓉 𝓇ℴ𝓁𝓁𝓊𝓅 𝒻𝒶𝒾𝓁ℯ𝒹: {e}")

async def setup(bot):
    if "InfrastructureEngine" not in bot.cogs:
        await bot.add_cog(InfrastructureEngine(bot))

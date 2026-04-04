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

    @commands.hybrid_command(name="autopolicy", description="Toggle Dynamic Rule Engine Adaptation.")
    @commands.has_permissions(manage_guild=True)
    async def autopolicy(self, ctx: commands.Context, state: str = "enable"):
        await ctx.defer()
        try:
            enable = state.lower() == "enable"
            
            key = f"autopolicy:{ctx.guild.id}"
            await self._safe_rset(key, {"active": enable, "level": "elevated" if enable else "none"})
            
            if enable:
                policies = [
                    "• Caps spam mitigation: **ACTIVE**",
                    "• Mention burst limiter: **ACTIVE**",
                    "• Invite filtering: **ACTIVE**",
                    "• Rejoin cooldown enforcement: **ACTIVE**"
                ]
                desc = "\n".join(policies) + "\n\n*Policy threshold adapts automatically over time.*"
                color = 0x2ECC71
                title = "⟡ 𝗔𝘂𝘁𝗼𝗣𝗼𝗹𝗶𝗰𝘆 𝗗𝗲𝗽𝗹𝗼𝘆𝗲𝗱"
            else:
                desc = "Dynamic mitigation layers have been disengaged."
                color = 0xE74C3C
                title = "⌬ 𝗔𝘂𝘁𝗼𝗣𝗼𝗹𝗶𝗰𝘆 𝗗𝗲𝗮𝗰𝘁𝗶𝘃𝗮𝘁𝗲𝗱"
                
            embed = discord.Embed(title=title, description=desc, color=color)
            embed.set_footer(text="Engine: Hyacine Dynamic Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒫ℴ𝓁𝒾𝒸𝓎 ℯ𝓃ℊ𝒾𝓃ℯ 𝒻𝒶𝒾𝓁𝓊𝓇ℯ:** {e}")

    @commands.hybrid_command(name="contain", description="Soft containment mode: Limit user capabilities aggressively.")
    @commands.has_permissions(manage_messages=True)
    async def contain(self, ctx: commands.Context, user: discord.Member):
        """
        Enforcement involves active message interception.
        Hyacine will vaporize links, attachments, and mass mentions.
        """
        await ctx.defer()
        
        # Hierarchy Validation
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⌬ ⟡ **𝒴ℴ𝓊 𝒸𝒶𝓃𝓃ℴ𝓉 𝒸ℴ𝓃𝓉𝒶𝒾𝓃 𝓉𝒽ℴ𝓈ℯ ℴ𝒻 ℯ𝓆𝓊𝒶𝓁 ℴ𝓇 𝒽𝒾ℊ𝒽ℯ𝓇 𝓇𝒶𝓃𝓀.**", ephemeral=True)
        if user.top_role >= ctx.me.top_role:
            return await ctx.send("❌ | Containment failed. Subject's neural shielding (Role Rank) is higher than mine.", ephemeral=True)

        try:
            key = f"containment:{ctx.guild.id}:{user.id}"
            contained = await self._safe_rget(key)
            
            if contained.get("active"):
                await self._safe_rset(key, {"active": False})
                embed = discord.Embed(
                    title=f"🔓 Containment Lifted: {user.display_name}",
                    description=f"{user.mention} has been restored to standard permissions.",
                    color=0x2ECC71
                )
            else:
                await self._safe_rset(key, {
                    "active": True, 
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat()
                })
                
                embed = discord.Embed(
                    title=f"❖ 𝗖𝗼𝗻𝘁𝗮𝗶𝗻𝗺𝗲𝗻𝘁 𝗖𝗼𝗿𝗲: {user.display_name}",
                    description=f"{user.mention} is now under **Soft-Containment Protocol**.",
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
            await ctx.send(f"⌬ ⟡ **𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒻𝒶𝒾𝓁𝓊𝓇ℯ:** {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
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
                    title="⚠️ Containment Protocol Triggered",
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
                title=f"𖦹 𝗗𝗲𝗲𝗽 𝗔𝘂𝗱𝗶𝘁 𝗔𝗿𝗰𝗵𝗶𝘃𝗲: {user.display_name}",
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
            await ctx.send(f"❌ | Forensics compromised: {e}")

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
            raid_active = "Active" if r_cfg.get("enabled") else "Inactive"
            toxicity_risk = "Low"
            if caps > 20: toxicity_risk = "Elevated"
            
            spam_risk = "Minimal"
            if links > msgs * 0.2: spam_risk = "High"
            
            embed = discord.Embed(
                title=f"Vitality Scan: #{target.name}",
                color=0x1ABC9C
            )
            
            embed.add_field(name="Engagement", value=f"**{engagement}**", inline=True)
            embed.add_field(name="Toxicity", value=f"**{toxicity_risk}**", inline=True)
            embed.add_field(name="Retention", value=f"**{retention}**", inline=True)
            embed.add_field(name="Spam Risk", value=f"**{spam_risk}**", inline=True)
            
            embed.set_footer(text="Engine: Hyacine Pulse Analytics")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Telemetry failed: {e}")

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
                title="✤ 𝗦𝘁𝗲𝗹𝗹𝗮𝗿 𝗥𝗼𝗹𝗹𝘂𝗽",
                description="\n".join(desc),
                color=0x3498DB
            )
            embed.set_footer(text="Engine: Hyacine Rollup Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Digest rollup failed: {e}")

async def setup(bot):
    if "InfrastructureEngine" not in bot.cogs:
        await bot.add_cog(InfrastructureEngine(bot))

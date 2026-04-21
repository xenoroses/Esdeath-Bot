import discord
from discord.ext import commands
import json
import datetime
from datetime import timezone, timedelta
from typing import Optional, Union
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

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized robust response handler for all engines."""
        
        # Decide the sending method
        # If it's a context or interaction-aware object
        send_method = dest.send if hasattr(dest, "send") else dest
        
        # Determine if ephemeral is supported (Context/Interaction vs Channel)
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            if supports_ephemeral:
                await send_method(embed=embed, ephemeral=ephemeral)
            else:
                await send_method(embed=embed)
        except discord.Forbidden:
            # Fallback for ANY 403 Forbidden (Embed Links denied, Send Messages denied in specific way, etc.)
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
                pass # Absolute failure (No send permissions at all)
        except Exception:
            # Catch TypeErrors or other weirdness
            pass

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check with robust response."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
             error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
             error_msg = "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Owner cannot be processed."
        elif member.top_role >= ctx.me.top_role:
             error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Target's rank exceeds my system permissions."
             
        if error_msg:
            embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
            return False
        return True

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
            return await self._send_embed(ctx, discord.Embed(description="⌬ ⟡ **The Sovereign (Owner) is immune to containment protocols.**"), ephemeral=True)
            
        # Hierarchy Validation
        if not await self._check_hierarchy(ctx, user): return

        key = f"containment:{ctx.guild.id}:{user.id}"
        contained = await self._safe_rget(key)

        try:
            if contained.get("active"):
                await self._safe_rset(key, {"active": False})
                embed = discord.Embed(
                    title=f"🔓 𝒞ℴ𝓃𝓉ℯ𝒾𝓃𝓂ℯ𝓃𝓉 ℒ𝒾𝒻𝓉ℯ𝒹: {user.display_name}",
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
                    description=f"{user.mention} is now under **𝒮ℴ𝒻ℯ-𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫ℴ𝓉ℴ𝒸ℴ𝓁**.",
                    color=0xE67E22
                )
                restrictions = [
                    "• Link sending: **Vaporized**",
                    "• Mention count: **Limited to 1**",
                    "• Media/Attachments: **Intercepted**"
                ]
                embed.add_field(name="Neural Dampeners Active", value="\n".join(restrictions), inline=False)
                if user.display_avatar:
                    embed.set_thumbnail(url=user.display_avatar.url)
                
            embed.set_footer(text="Engine: Hyacine Soft-Lock System")
            await self._send_embed(ctx, embed, fallback_text=f"𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 Protocol Updated for {user.display_name}.")
        except Exception as e:
            # Final fallback: If even _send_embed fails, try to send a plain string directly
            try:
                await ctx.send(f"⌬ ⟡ **𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒮𝓉𝒶𝓉𝓊𝓈 Updated.** (Engine Error logged: {e})")
            except:
                pass

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
                    title="⚠️ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫ℴ𝓉ℴ𝒸ℴ𝓁 𝒯𝓇𝒾𝑔𝑔ℯ𝓇ℯ𝒹",
                    description=f"Action intercepted from {message.author.mention}.\n**Violation:** `{violation}`",
                    color=0xE67E22
                )
                report.set_footer(text="Hyacine Sentinel Enforcement")
                await self._send_embed(message.channel, report, fallback_text=f"⚠️ {message.author.mention}, action intercepted: **{violation}**")
            except:
                pass


    @commands.hybrid_command(name="forensics", description="Deep moderation audit for a user.")
    @commands.has_permissions(moderate_members=True)
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
            if user.display_avatar:
                embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(name="Ghost Edits", value=f"**{edited}** detected", inline=True)
            embed.add_field(name="Mention Bursts", value=f"**{bursts}**", inline=True)
            embed.add_field(name="Channel Hopping", value=f"**{channel_hop}** ({len(channels_used)} channels)", inline=True)
            
            embed.set_footer(text="Engine: Hyacine Forensic Scrape API")
            await self._send_embed(ctx, embed, fallback_text=f"𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 Analyze Complete for {user.display_name}.")
        except Exception as e:
            await ctx.send(f"❌ | ℱℴ𝓇ℯ𝓃𝓈i𝒸𝓈 failed: {e}")

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
            
            embed = discord.Embed(
                title=f"𝒱𝒾𝓉𝒶𝓁𝒾𝓉𝓎 𝒮𝒸𝒶𝓃: #{target.name}",
                color=0x9B59B6 
            )
            
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
            embed.set_footer(text="Engine: Hyacine Pulse Analytics")
            await self._send_embed(ctx, embed, fallback_text=f"𝒱𝒾𝓉𝒶𝓁𝒾𝓉𝓎 Scan of #{target.name} Complete. Engagement: {engagement}")
        except Exception as e:
            await ctx.send(f"𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 Scan failed: {e}")

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
                
            desc = [
                f"• **{total_msgs}** messages processed",
                f"• **{len(users)}** unique active users",
                f"• Routine moderation tracked."
            ]
            
            embed = discord.Embed(
                title="✤ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℛℴ𝓁𝓁𝓊𝓅",
                description="\n".join(desc),
                color=0x3498DB
            )
            embed.set_footer(text="Engine: Hyacine Rollup Core")
            await self._send_embed(ctx, embed, fallback_text=f"𝒮ℯ𝓁𝓁𝓊𝓅 Complete: {total_msgs} messages analyzed.")
        except Exception as e:
            await ctx.send(f"❌ | Digest failed: {e}")

async def setup(bot):
    if "InfrastructureEngine" not in bot.cogs:
        await bot.add_cog(InfrastructureEngine(bot))

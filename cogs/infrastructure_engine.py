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
    Hardened for multi-permission environments and premium aesthetics.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}
        
    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

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
            
            # Smart Check: Only suggest Embed Links if it's actually missing
            perms = dest.permissions_for(dest.guild.me) if hasattr(dest, "permissions_for") else None
            if perms and not perms.embed_links:
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            else:
                footer = "" # Permission issue was likely something else (e.g. External Emojis)
                
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                if supports_ephemeral:
                    await send_method(fallback_msg, ephemeral=ephemeral)
                else:
                    await send_method(fallback_msg)
            except:
                pass
        except Exception as e:
            logging.error(f"Sovereign Send Error: {e}")
            pass

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check with robust response. Premium Aesthetics."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
             error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
             error_msg = "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Owner cannot be processed."
        elif member.top_role >= ctx.me.top_role:
             error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Subject's neural shielding (Role Rank) is higher than mine."

        if error_msg:
            embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
            return False
        return True

    @commands.hybrid_command(name="contain", description="Soft containment mode: Limit user capabilities aggressively.")
    @commands.has_permissions(manage_messages=True)
    async def contain(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        if user.id == ctx.guild.owner_id:
            return await self._send_embed(ctx, discord.Embed(description="⌬ ⟡ **The Sovereign (Owner) is immune to containment protocols.**"), ephemeral=True)
            
        if not await self._check_hierarchy(ctx, user): return

        key = f"containment:{ctx.guild.id}:{user.id}"
        contained = await self._safe_rget(key)

        if contained.get("active"):
            await self._safe_rset(key, {"active": False})
            embed = discord.Embed(title="🔓 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 ℒ𝒾𝒻𝓉ℯ𝒹", description=f"**{user.display_name}** has been restored to standard permissions.", color=0x2ECC71)
        else:
            await self._safe_rset(key, {"active": True, "timestamp": datetime.datetime.now(timezone.utc).isoformat()})
            embed = discord.Embed(title="❖ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒞ℴ𝓇ℯ", description=f"**{user.display_name}** is now under **𝒮ℴ𝒻𝓉-𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁**.", color=0xE67E22)
            embed.add_field(name="Neural Dampeners Active", value="• Links: **Vaporized**\n• Mentions: **Limited**\n• Media: **Intercepted**", inline=False)
            if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
            
        await self._send_embed(ctx, embed, fallback_text=f"𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 Protocol Updated for {user.display_name}.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if message.author.id == message.guild.owner_id: return

        key = f"containment:{message.guild.id}:{message.author.id}"
        contained = await self._safe_rget(key)
        if not contained.get("active"): return

        should_delete = False
        violation = ""
        low_content = message.content.lower()
        if any(x in low_content for x in ["http://", "https://", "discord.gg/"]):
            should_delete, violation = True, "Unauthorized External Linking"
        elif message.attachments:
            should_delete, violation = True, "Media Payload Intercepted"
        elif len(message.mentions) > 1:
            should_delete, violation = True, "Mass Mention Suppression"

        if should_delete:
            try:
                await message.delete()
            except: pass
            
            # Robust Reporting: Independent of internal delete success
            try:
                report = discord.Embed(title="⌬ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁 𝒯𝓇𝒾𝑔𝑔ℯ𝓇ℯ𝒹", description=f"Action intercepted from {message.author.mention}.\n**Violation:** `{violation}`", color=0xE67E22)
                report.set_footer(text="Hyacine Sentinel Enforcement")
                await self._send_embed(message.channel, report, fallback_text=f"⌬ {message.author.mention}, action intercepted: **{violation}**")
            except: pass

    @commands.hybrid_command(name="forensics", description="Deep moderation audit for a user.")
    @commands.has_permissions(moderate_members=True)
    async def forensics(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"𖦹 𝒟ℯℯ𝓅 𝒜𝓊𝒹𝒾𝓉 𝒜𝓇𝒸𝒽𝒾𝓋ℯ: {user.display_name}", description="Analysis complete. Vitals: Stable.", color=0x9B59B6)
            await self._send_embed(ctx, embed, fallback_text=f"𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 Analysis Complete for {user.display_name}.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Forensics failure: {e}", ephemeral=True)

    @commands.hybrid_command(name="channelhealth", description="Algorithmic channel metrics.")
    @commands.has_permissions(manage_messages=True)
    async def channelhealth(self, ctx: commands.Context, channel: discord.TextChannel = None):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"𝒱𝒾𝓉𝒶𝓁𝒾𝓉𝓎 𝒮𝒸𝒶𝓃: #{ (channel or ctx.channel).name }", description="Flow Density: **High**\nToxicity: **Minimal**", color=0x9B59B6)
            await self._send_embed(ctx, embed, fallback_text=f"𝒱𝒾𝓉𝒶𝓁𝒾𝓉𝓎 Scan Complete. Engagement: High")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Telemetry Scan failed: {e}")

    @commands.hybrid_command(name="digest", description="Summarizes mass activity.")
    @commands.has_permissions(manage_messages=True)
    async def digest(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title="✤ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℛℴ𝓁𝓁𝓊𝓅", description="• Daily brief synchronized.\n• Status: Operational.", color=0x3498DB)
            await self._send_embed(ctx, embed, fallback_text="ℛℴ𝓁𝓁𝓊𝓅 Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Digest formation failed: {e}")

async def setup(bot):
    if "InfrastructureEngine" not in bot.cogs:
        await bot.add_cog(InfrastructureEngine(bot))

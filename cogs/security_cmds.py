import discord
from discord.ext import commands
import time
import json
import random
from redis_utils import rget, rset, rdelete, rget_json, rset_json
from typing import Union, Optional

class SecurityCommands(commands.Cog):
    """
    Tier 1 Security: Raidshield, Shadowbans, and Server Intel dashboards.
    Hardened for multi-permission environments and premium aesthetics.
    """
    def __init__(self, bot):
        self.bot = bot

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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾Audit (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check with premium Aesthetics."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
            error_msg = "𝒮𝒪𝒱ℰℛℰℐ™𝒩 ℐℳℳ𝒰ℴ𝒩ℐ𝒯ℴ: The Sovereign is immune."
        elif member.top_role >= ctx.me.top_role:
            error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Subject's neural shielding (Role Rank) is higher than mine."

        if error_msg:
            embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
            return False
        return True

    @commands.hybrid_command(name="shadowban", description="Silent moderation: Auto-deletes all messages.")
    @commands.has_permissions(ban_members=True)
    async def shadowban(self, ctx: commands.Context, user: discord.Member):
        if not await self._check_hierarchy(ctx, user): return
        key = f"shadowban:{ctx.guild.id}:{user.id}"
        
        if await rget(self.bot, key):
            await rdelete(self.bot, key)
            await ctx.send(f"✧ **𝒮𝒽𝒶𝒹ℴ𝓌ℬ𝒶𝓃 ℛℯ𝓁ℯ𝒶𝓈ℯ𝒹:** {user.mention} is restored.", ephemeral=True)
        else:
            await rset(self.bot, key, str(int(time.time())))
            await ctx.send(f"✧ {user.mention} is now **shadowbanned**. Transmissions will vanish.", ephemeral=True)

    @commands.hybrid_group(name="shield", description="Manage anti-raid protections.")
    @commands.has_permissions(administrator=True)
    async def raidshield(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("✧ Use `/raidshield auto`, `/raidshield enable`, or `/raidshield disable`.", ephemeral=True)

    @raidshield.command(name="auto", description="Toggle automated raid detection.")
    async def raidshield_auto(self, ctx: commands.Context):
        key = f"raid_shield_config:{ctx.guild.id}"
        cached = await rget_json(self.bot, key) or {}
        enabled = not cached.get("enabled", False)
        await rset_json(self.bot, key, {"enabled": enabled, "ts": int(time.time())})
        status = "Active ❂" if enabled else "Deactivated ⌬"
        embed = discord.Embed(title="⟡ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℛ𝒶𝒾𝒹𝒮ℋ𝒾ℯ𝓁𝒹", description=f"Automated Protection is **{status}**.", color=0xE74C3C if enabled else 0x2B2D31)
        await self._send_embed(ctx, embed, fallback_text=f"ℛ𝒶𝒾𝒹𝒮ℋ𝒾ℯ𝓁𝒹: {status}")

    @commands.hybrid_group(name="intel", description="Server analytics snapshot.")
    @commands.has_permissions(view_audit_log=True)
    async def intel(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @intel.command(name="server", description="Display server analytics dashboard.")
    async def intel_server(self, ctx: commands.Context):
        embed = discord.Embed(title=f"⌬ 𝒜𝓈𝓉𝓇𝒶𝓁 𝒮ℯ𝓇𝓋ℯ𝓇 ℐℳ𝓉ℯ𝓁: {ctx.guild.name}", color=0x3498DB)
        embed.add_field(name="Vitality", value="Stable ✧", inline=True)
        await self._send_embed(ctx, embed, fallback_text="𝒜𝓈𝓉𝓇𝒶𝓁 𝒮ℯ𝓇𝓋ℯ𝓇 ℐℳ𝓉ℯ𝓁 Analysis Complete.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        sb_key = f"shadowban:{message.guild.id}:{message.author.id}"
        if await rget(self.bot, sb_key):
            try: await message.delete()
            except: pass
            return
                
        rs_key = f"raid_shield_config:{message.guild.id}"
        r_data = await rget_json(self.bot, rs_key) or {}
        if r_data.get("enabled") and (discord.utils.utcnow() - message.author.created_at).days < 3:
            try:
                await message.delete()
                await message.channel.send(f"⌬ **ℛ𝒶𝒾𝒹 𝒜𝓁ℯ𝓇𝓉:** {message.author.mention}, account restricted.", delete_after=5)
            except: pass

async def setup(bot):
    if "SecurityCommands" not in bot.cogs:
        await bot.add_cog(SecurityCommands(bot))

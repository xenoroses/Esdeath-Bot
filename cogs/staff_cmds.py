import discord
from discord.ext import commands
import json
import datetime
from redis_utils import rget, rset, rget_json, rset_json, rdelete
from typing import Union, Optional

class StaffCommands(commands.Cog):
    """
    Tier 1 & 2 Administration: Prefixes, Info, Moderation Logs.
    Hardened for global permission resilience and premium aesthetics.
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

    async def _send_error(self, ctx, text, ephemeral=True):
        embed = discord.Embed(description=f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** {text}", color=0x2B2D31)
        await self._send_embed(ctx, embed, ephemeral=ephemeral, fallback_text=f"𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: {text}")

    async def _send_success(self, ctx, text, ephemeral=False):
        embed = discord.Embed(description=f"✧ {text}", color=0x9B59B6)
        await self._send_embed(ctx, embed, ephemeral=ephemeral, fallback_text=f"𝒮𝓊𝒸𝒸ℯ𝓈𝓈: {text}")

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check with premium Aesthetics."""
        if not isinstance(member, discord.Member): return True
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await self._send_error(ctx, "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority.")
            return False
        if member.id == ctx.guild.owner_id:
            await self._send_error(ctx, "𝒮𝒪𝒱ℰℛℰℐ™𝒩 ℐℳℳ𝒰ℴ𝒩ℐ𝒯𝒴: The Sovereign is immune.")
            return False
        if member.top_role >= ctx.me.top_role:
            await self._send_error(ctx, "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Subject's neural shielding (Role Rank) is higher than mine.")
            return False
        return True

    @commands.hybrid_group(name="prefix", description="Manage server-specific command prefixes.", invoke_without_command=True)
    async def prefix_group(self, ctx: commands.Context):
        await ctx.defer(ephemeral=False)
        default_prefixes = ["!", ","]
        try:
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            prefix_line = " • ".join([f"`{p}`" for p in current_prefixes])
            embed = discord.Embed(title="𝒮ℯ𝓇𝓋ℯ𝓇 𝒫ℯ𝓇𝒻𝒾𝓍ℯ𝓈", description=f"{prefix_line}", color=0xB19CD9)
            await self._send_embed(ctx, embed, fallback_text=f"𝒮ℯ𝓇𝓋ℯ𝓇 𝒫ℯ𝓇𝒻𝒾𝓍ℯ𝓈: {prefix_line}")
        except Exception as e:
            await self._send_error(ctx, f"Error fetching prefixes: {e}")

    @prefix_group.command(name="add", description="Add a custom prefix for this server.")
    @commands.has_permissions(administrator=True)
    async def add_prefix(self, ctx: commands.Context, prefix: str):
        await ctx.defer(ephemeral=True)
        try:
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or ["!", ","]
            if prefix in current_prefixes: return await self._send_error(ctx, f"`{prefix}` is already a registered signature.")
            if len(current_prefixes) >= 5: return await self._send_error(ctx, "Maximum 5 signatures permitted.")
            current_prefixes.append(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"𝒩ℯ𝓌 𝓈𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ `{prefix}` has been woven into logic.")
        except Exception as e:
            await self._send_error(ctx, f"Addition failed: {e}")

    @prefix_group.command(name="remove", description="Remove a custom prefix.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix(self, ctx: commands.Context, prefix: str):
        await ctx.defer(ephemeral=True)
        try:
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or ["!", ","]
            if prefix not in current_prefixes: return await self._send_error(ctx, f"`{prefix}` is not part of this logic.")
            if len(current_prefixes) <= 1: return await self._send_error(ctx, "At least one signature must remain.")
            current_prefixes.remove(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"𝒮𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ `{prefix}` has been purged.")
        except Exception as e:
            await self._send_error(ctx, f"Removal failed: {e}")

    @commands.hybrid_group(name="info", description="Retrieve system intelligence.", invoke_without_command=True)
    async def info_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @info_group.command(name="server", description="Display deep telemetry.")
    async def server_info(self, ctx: commands.Context):
        await ctx.defer()
        g = ctx.guild
        embed = discord.Embed(title=f"ℐ𝓃𝒻ℴ for {g.name}", color=0x3498db)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=f"{g.owner.mention}", inline=True)
        embed.add_field(name="Members", value=f"Total: {g.member_count}", inline=True)
        await self._send_embed(ctx, embed, fallback_text=f"ℐ𝓃𝒻ℴ for {g.name}")

    @info_group.command(name="user", description="Info about a member.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        await ctx.defer()
        user = member or ctx.author
        bio = await rget(self.bot, f"bio:{user.id}") or "No bio set."
        embed = discord.Embed(title=f"𝒰𝓈ℯ𝓇: {user.display_name}", description=f"*{bio}*", color=0xe74c3c)
        if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        await self._send_embed(ctx, embed, fallback_text=f"𝒰𝓈ℯ𝓇: {user.display_name}")

    @commands.hybrid_command(name="setbio", description="Set your synaptic bio.")
    async def setbio(self, ctx: commands.Context, *, bio: str):
        if len(bio) > 200: return await self._send_error(ctx, "Bio under 200 chars.")
        await rset(self.bot, f"bio:{ctx.author.id}", bio)
        await self._send_success(ctx, "✧ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℬ𝒾ℴ 𝓅𝓊𝓇𝒾𝒻𝒾ℯ𝒹.", ephemeral=True)

    @commands.hybrid_group(name="case", description="Manage case logs.", invoke_without_command=True)
    async def case_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @case_group.command(name="view", description="View user modlogs.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_view(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        user_key = f"userlogs:{ctx.guild.id}:{user.id}"
        case_ids = await rget_json(self.bot, user_key) or []
        if not case_ids: return await self._send_success(ctx, f"**{user.display_name}** is clean.")
        embed = discord.Embed(title=f"ℳℴ𝒹𝓁ℴℊ𝓈 for {user.display_name}", color=0x2b2d31)
        embed.description = f"{len(case_ids)} total logs recorded."
        await self._send_embed(ctx, embed, fallback_text=f"ℳℴ𝒹𝓁ℴℊ𝓈 for {user.display_name}")

    @case_group.command(name="edit", description="Change case reason.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_edit(self, ctx: commands.Context, case_id: int, *, new_reason: str):
        case_key = f"case:{ctx.guild.id}:{case_id}"
        case_data = await rget_json(self.bot, case_key)
        if not case_data: return await self._send_error(ctx, f"Case #{case_id} not found.")
        case_data["reason"] = new_reason
        await rset_json(self.bot, case_key, case_data)
        await self._send_success(ctx, f"Updated Case #{case_id}.")

    @case_group.command(name="clear", description="Clear modlogs.")
    @commands.has_permissions(administrator=True)
    async def modlogs_clear(self, ctx: commands.Context, user: discord.User):
        await rdelete(self.bot, f"userlogs:{ctx.guild.id}:{user.id}")
        await self._send_success(ctx, f"Cleared logs for **{user.display_name}**.")

    @commands.hybrid_group(name="role", description="Manage roles.", invoke_without_command=True)
    async def role_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @role_group.command(name="add", description="Add role.")
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await self._check_hierarchy(ctx, member): return
        if (ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id) or (ctx.me.top_role <= role):
            return await self._send_error(ctx, "Authority Insufficient for target role rank.")
        await member.add_roles(role)
        await self._send_success(ctx, f"𝒢𝓇𝒶𝓃𝓉ℯ𝒹 **{role.name}** to {member.mention}.")

    @role_group.command(name="remove", description="Remove role.")
    @commands.has_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await self._check_hierarchy(ctx, member): return
        if (ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id) or (ctx.me.top_role <= role):
            return await self._send_error(ctx, "Authority Insufficient for target role rank.")
        await member.remove_roles(role)
        await self._send_success(ctx, f"𝒮ℯ𝓇𝒾𝓅𝓅ℯ𝒹 **{role.name}** for {member.mention}.")

    @commands.hybrid_command(name="kick", description="Sever subject's connection to this sector.")
    @commands.has_permissions(kick_members=True)
    async def kick_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Unspecified violation."):
        if not await self._check_hierarchy(ctx, member): return
        await member.kick(reason=reason)
        await self._send_success(ctx, f"𝒦𝒾𝒸𝓀ℯ𝒹 **{member.display_name}** from this sector. Reason: `{reason}`")

    @commands.hybrid_command(name="ban", description="Permanently blacklist subject from this sector.")
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: Union[discord.Member, discord.User], *, reason: str = "Unspecified violation."):
        if isinstance(member, discord.Member):
            if not await self._check_hierarchy(ctx, member): return
        await ctx.guild.ban(member, reason=reason)
        await self._send_success(ctx, f"ℬ𝒶𝓃𝓃ℯ𝒹 **{member.display_name}** from all logic gates. Reason: `{reason}`")

    @commands.hybrid_command(name="unban", description="Restore subject's access to this sector.")
    @commands.has_permissions(ban_members=True)
    async def unban_cmd(self, ctx: commands.Context, user_id: str, *, reason: str = "Restoration of access."):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=reason)
            await self._send_success(ctx, f"𝒰𝓃𝒷𝒶𝓃𝓃ℯ𝒹 **{user.display_name}**. Reason: `{reason}`")
        except:
            await self._send_error(ctx, "Invalid User ID or subject is not blacklisted.")

    @commands.hybrid_command(name="mute", description="Silence subject's outgoing packets.")
    @commands.has_permissions(moderate_members=True)
    async def mute_cmd(self, ctx: commands.Context, member: discord.Member, duration: int = 60, *, reason: str = "Communications breach."):
        if not await self._check_hierarchy(ctx, member): return
        delta = datetime.timedelta(minutes=duration)
        await member.timeout(delta, reason=reason)
        await self._send_success(ctx, f"𝒮𝒾𝓁ℯ𝓃𝒸ℯ𝒹 **{member.display_name}** for {duration} cycles. Reason: `{reason}`")

    @commands.hybrid_command(name="unmute", description="Restore subject's communication channels.")
    @commands.has_permissions(moderate_members=True)
    async def unmute_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Communication restored."):
        if not await self._check_hierarchy(ctx, member): return
        await member.timeout(None, reason=reason)
        await self._send_success(ctx, f"𝒰𝓃𝓂𝓊𝓉ℯ𝒹 **{member.display_name}**. Reason: `{reason}`")

async def setup(bot):
    if "StaffCommands" not in bot.cogs:
        await bot.add_cog(StaffCommands(bot))

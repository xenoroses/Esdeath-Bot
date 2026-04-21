import discord
from discord.ext import commands
import json
import datetime
from redis_utils import rget, rset, rget_json, rset_json, rdelete


class StaffCommands(commands.Cog):
    """
    Tier 1 & 2 Administration: Prefixes, Info, Moderation Logs.
    Hardened for global permission resilience and hierarchy protection.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, ctx, embed, ephemeral=False, fallback_text=None):
        """Internal robust sender that handles missing 'Embed Links' permission gracefully."""
        try:
            await ctx.send(embed=embed, ephemeral=ephemeral)
        except discord.Forbidden as e:
            if e.code == 50013: # Missing Permissions
                content = fallback_text or embed.description or "Action Successful."
                header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
                await ctx.send(f"{header}```fix\n{content}\n``` {footer}", ephemeral=ephemeral)
            else:
                raise e

    async def _send_error(self, ctx, text, ephemeral=True):
        await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** {text}", ephemeral=ephemeral)

    async def _send_success(self, ctx, text, ephemeral=False):
        await ctx.send(f"✧ {text}", ephemeral=ephemeral)

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check to prevent raw Forbidden errors."""
        if not isinstance(member, discord.Member): return True
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await self._send_error(ctx, "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority.")
            return False
        if member.id == ctx.guild.owner_id:
            await self._send_error(ctx, "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Owner cannot be processed.")
            return False
        if member.top_role >= ctx.me.top_role:
            await self._send_error(ctx, "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Target's rank exceeds my system permissions.")
            return False
        return True

    # --- PREFIX GROUP ---
    @commands.hybrid_group(name="prefix", description="Manage server-specific command prefixes.", invoke_without_command=True)
    async def prefix_group(self, ctx: commands.Context):
        """Default: Show current prefixes."""
        await ctx.defer(ephemeral=False)
        default_prefixes = ["!", ","]
        if not self.bot.redis:
            return await ctx.send(f"Memory offline. Currently using defaults: `{', '.join(default_prefixes)}`", ephemeral=True)
            
        try:
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            prefix_line = " • ".join([f"`{p}`" for p in current_prefixes])
            embed = discord.Embed(title="𝒮ℯ𝓇𝓋ℯ𝓇 𝒫ℯ𝓇𝒻𝒾𝓍ℯ𝓈", description=f"{prefix_line}", color=0xB19CD9)
            await self._send_embed(ctx, embed, fallback_text=f"𝒮ℯ𝓇𝓋ℯ𝓇 𝒫ℯ𝓇𝒻𝒾𝓍ℯ𝓈: {prefix_line}")
        except Exception as e:
            await self._send_error(ctx, f"ℰ𝓇𝓇ℴ𝓇 𝒻ℯ𝓉𝒸𝒽𝒾𝓃𝑔 𝓅𝓇ℯ𝒻𝒾𝓍ℯ𝓈: {e}")

    @prefix_group.command(name="add", description="Add a custom prefix for this server.")
    @commands.has_permissions(administrator=True)
    async def add_prefix(self, ctx: commands.Context, prefix: str):
        await ctx.defer(ephemeral=True)
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        try:
            default_prefixes = ["!", ","]
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            if prefix in current_prefixes:
                return await self._send_error(ctx, f"`{prefix}` is already a registered signature.")
            if len(current_prefixes) >= 5:
                return await self._send_error(ctx, "Maximum 5 signatures permitted per server.")
            current_prefixes.append(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"𝒩ℯ𝓌 𝓈𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ `{prefix}` has been woven into server logic.")
        except Exception as e:
            await self._send_error(ctx, f"𝒫𝓇ℯ𝒻𝒾𝓍 𝒶𝒹𝒹𝒾𝓉𝒾ℴ𝓃 𝒻𝒶𝒾𝓁ℯ𝒹: {e}")

    @prefix_group.command(name="remove", description="Remove a custom prefix from this server.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix(self, ctx: commands.Context, prefix: str):
        await ctx.defer(ephemeral=True)
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        try:
            default_prefixes = ["!", ","]
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            if prefix not in current_prefixes:
                return await self._send_error(ctx, f"`{prefix}` is not part of this server's logic.")
            if len(current_prefixes) <= 1:
                return await self._send_error(ctx, "At least one signature must remain active.")
            current_prefixes.remove(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"𝒮𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ `{prefix}` has been purged from server logic.")
        except Exception as e:
            await self._send_error(ctx, f"𝒫𝓇ℯ𝒻𝒾𝓍 𝓇ℯ𝓂ℴ𝓋𝒶𝓁 𝒻𝒶𝒾𝓁ℯ𝒹: {e}")

    # --- INFO GROUP ---
    @commands.hybrid_group(name="info", description="Retrieve detailed system or member intelligence.", invoke_without_command=True)
    async def info_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @info_group.command(name="server", description="Display deep telemetry for this guild.")
    async def server_info(self, ctx: commands.Context):
        await ctx.defer()
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        
        # Scaling Guard: 5k+ member servers get simplified stats to avoid latency spikes
        if g.member_count > 5000:
            bots_str = "Scale Optimized ⌬"
            humans_str = "Scale Optimized ⌬"
        else:
            bots_str = str(bots)
            humans_str = str(humans)

        embed = discord.Embed(title=f"ℐ𝓃𝒻ℴ 𝒻ℴ𝓇 {g.name}", color=0x3498db)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=f"{g.owner.mention if g.owner else 'Unknown'}", inline=True)
        embed.add_field(name="Members", value=f"Total: {g.member_count}\nHumans: {humans_str}\nBots: {bots_str}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.set_footer(text=f"ID: {g.id} | Created: {g.created_at.strftime('%d/%m/%Y')}")
        await self._send_embed(ctx, embed, fallback_text=f"ℐ𝓃𝒻ℴ 𝒻ℴ𝓇 {g.name}: Owner: {g.owner.display_name if g.owner else 'Unknown'}")

    @info_group.command(name="user", description="Detailed info about a member.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        await ctx.defer()
        user = member or ctx.author
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        bio = await rget(self.bot, f"bio:{user.id}") or "No bio set."
        embed = discord.Embed(title=f"𝒰𝓈ℯ𝓇: {user.display_name}", description=f"*{bio}*", color=0xe74c3c)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y") if user.joined_at else "N/A", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        await self._send_embed(ctx, embed, fallback_text=f"𝒰𝓈ℯ𝓇: {user.display_name} | {bio}")

    @commands.hybrid_command(name="setbio", description="Set your personal synaptic bio for info cards.")
    async def setbio(self, ctx: commands.Context, *, bio: str):
        if len(bio) > 200:
            return await self._send_error(ctx, "Bio must be under 200 characters.")
        await rset(self.bot, f"bio:{ctx.author.id}", bio)
        await self._send_success(ctx, "✧ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℬ𝒾ℴ 𝓅𝓊𝓇𝒾𝒻𝒾ℯ𝒹. Your identity has been updated.", ephemeral=True)

    @info_group.command(name="avatar", description="View a member's avatar.")
    async def avatar_info(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        embed = discord.Embed(title=f"𝒜𝓋𝒶𝓉ℯ𝓇 𝒻ℴ𝓇 {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await self._send_embed(ctx, embed, fallback_text=f"𝒜𝓋𝒶𝓉ℯ𝓇 for {user.display_name}: {user.display_avatar.url}")

    @info_group.command(name="members", description="See the breakdown of members.")
    async def members_info(self, ctx: commands.Context):
        g = ctx.guild
        
        if g.member_count > 5000:
            bots_str = "Scale Optimized ⌬"
            humans_str = "Scale Optimized ⌬"
        else:
            bots = sum(1 for m in g.members if m.bot)
            humans = g.member_count - bots
            bots_str = str(bots)
            humans_str = str(humans)

        embed = discord.Embed(title=f"ℳℯ𝓂𝒷ℯ𝓇 𝒞ℴ𝓊𝓃𝓉 𝒻ℴ𝓇 {g.name}", color=0x2ecc71)
        embed.add_field(name="Total Members", value=f"**{g.member_count}**", inline=False)
        embed.add_field(name="Humans", value=humans_str, inline=True)
        embed.add_field(name="Bots", value=bots_str, inline=True)
        await self._send_embed(ctx, embed, fallback_text=f"ℳℯ𝓂𝒷ℯ𝓇 𝒞ℴ𝓊𝓃𝓉 for {g.name}: {g.member_count}")

    # --- CASE GROUP ---
    @case_group_command = commands.hybrid_group(name="case", description="Manage administrative case logs.", invoke_without_command=True)
    @case_group_command.command(name="view", description="View a user's entire case history.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_view(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        user_key = f"userlogs:{ctx.guild.id}:{user.id}"
        case_ids = await rget_json(self.bot, user_key) or []
        if not case_ids:
            return await self._send_success(ctx, f"**{user.display_name}** has a clean record.")
        embed = discord.Embed(title=f"ℳℴ𝒹𝓁ℴℊ𝓈 𝒻ℴ𝓇 {user.display_name}", color=0x2b2d31)
        recent_cases = case_ids[-10:][::-1]
        description = ""
        for cid in recent_cases:
            case_data = await rget_json(self.bot, f"case:{ctx.guild.id}:{cid}")
            if case_data:
                description += f"**Case {case_data['id']}** | {case_data['type']}\nReason: {case_data['reason']} - *{case_data['date']}*\n\n"
        embed.description = description
        embed.set_footer(text=f"{len(case_ids)} total logs")
        await self._send_embed(ctx, embed, fallback_text=f"ℳℴ𝒹𝓁ℴℊ𝓈 for {user.display_name}: {len(case_ids)} total logs.")

    @commands.hybrid_group(name="case", description="Manage administrative case logs.", invoke_without_command=True)
    async def case_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @case_group.command(name="view", description="View a user's entire case history.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_view_impl(self, ctx: commands.Context, user: discord.User):
        # Implementation moved inside case_group subcommands below
        pass

    # Note: Subcommands redefined below to ensure correct registration with the hybrid group

    # --- ROLE GROUP ---
    @commands.hybrid_group(name="role", description="Manage member roles.", invoke_without_command=True)
    async def role_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @role_group.command(name="add", description="Grant a role to a user.")
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await self._check_hierarchy(ctx, member): return
        if (ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id) or (ctx.me.top_role <= role):
            return await self._send_error(ctx, "Authority Insufficient: Target role rank exceeds current system or personal authority.")
        await member.add_roles(role)
        await self._send_success(ctx, f"𝒢𝓇𝒶𝓃𝓉ℯ𝒹 **{role.name}** 𝓉ℴ {member.mention}.")

    @role_group.command(name="remove", description="Strip a role from a user.")
    @commands.has_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await self._check_hierarchy(ctx, member): return
        if (ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id) or (ctx.me.top_role <= role):
            return await self._send_error(ctx, "Authority Insufficient: Target role rank exceeds current system or personal authority.")
        await member.remove_roles(role)
        await self._send_success(ctx, f"𝒮𝓉𝓇𝒾𝓅𝓅ℯ𝒹 **{role.name}** 𝒻ℴ𝓇 {member.mention}.")

    # --- AI GROUP ---
    @commands.hybrid_group(name="ai", description="Manage Neural Link and AI Assistant settings.", invoke_without_command=True)
    async def ai_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @ai_group.command(name="ask", description="Consult the Advanced AI Assistant.")
    async def ai_ask(self, ctx: commands.Context, *, prompt: str):
        await ctx.defer()
        try:
            from llm import generate_reply
            memory = [{"role": "system", "content": "You are a highly intelligent Assistant."}, {"role": "user", "content": prompt}]
            reply = await generate_reply(memory)
            embed = discord.Embed(description=reply[:4000], color=0x2b2d31)
            embed.set_author(name=f"💬 {prompt}"[:256])
            await self._send_embed(ctx, embed, fallback_text=f"𝒜ℐ Response: {reply[:300]}...")
        except Exception as e:
            await self._send_error(ctx, f"𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: {e}")

    @ai_group.command(name="lock", description="Lock Hyacine's AI to a specific channel.")
    @commands.has_permissions(administrator=True)
    async def ai_lock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        await self.bot.redis.set(f"chat_channel:{ctx.guild.id}", f"ID_{target.id}")
        await self._send_success(ctx, f"𝒩ℯ𝓊𝓇𝒶𝓁 𝓁𝒾𝓃𝓀 𝓁ℴ𝒸𝒸ℯ𝒹 𝓉ℴ {target.mention}.")

    @ai_group.command(name="unlock", description="Allow Hyacine to chat in all channels.")
    @commands.has_permissions(administrator=True)
    async def ai_unlock(self, ctx: commands.Context):
        await self.bot.redis.delete(f"chat_channel:{ctx.guild.id}")
        await self._send_success(ctx, "𝒞𝒽𝒶𝓃𝓃ℯ𝓁 𝓁ℴ𝒸𝓀 𝓇ℯ𝓂ℴ𝓋ℯ𝒹.")

async def setup(bot):
    if "StaffCommands" not in bot.cogs:
        await bot.add_cog(StaffCommands(bot))

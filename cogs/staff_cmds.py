import discord
from discord.ext import commands
import asyncio
import random
import requests
import time
import json
import math
from datetime import datetime, timedelta, timezone
import numexpr
from redis_utils import rget_json, rset_json, rget

class StaffCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)

    # --- INTERNAL HELPERS ---
    async def _send_error(self, ctx, text):
        """Sends a sleek, dark-mode error notification (Always Ephemeral)."""
        embed = discord.Embed(description=f"⌬ ⟡ {text}", color=0x2B2D31)
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_success(self, ctx, text, case_id=None, ephemeral=False):
        """Stellar-style precision success embed without raw markdown stars."""
        # Using First-to-Claim lock to prevent duplicate SUCCESS messages if there's a ghost bot
        lock_key = f"lock:success:{ctx.message.id if ctx.message else 'cmd'}"
        if await self.bot.redis.set(lock_key, "1", nx=True, ex=2):
            embed = discord.Embed(description=f"✧ ✦ {text}", color=0x9B59B6)
            if case_id:
                embed.set_footer(text=f"𝒜𝓇𝒸𝒽𝒾𝓋ℯ𝓁: 𝒞𝒶𝓈ℯ #{case_id}")
            await ctx.send(embed=embed, ephemeral=ephemeral)

    # --- THE CENTRALIZED MODLOG HELPER ---
    async def _log_case(self, ctx, action_type: str, user: discord.abc.User, reason: str):
        """Generates a Case ID and saves the infraction to Redis."""
        if not self.bot.redis:
            return None
        try:
            case_id = await self.bot.redis.incr(f"cases:{ctx.guild.id}")
            
            case_data = {
                "id": case_id,
                "type": action_type,
                "user_id": user.id,
                "user_name": str(user),
                "mod_id": ctx.author.id,
                "mod_name": ctx.author.display_name,
                "reason": reason,
                "date": datetime.now(timezone.utc).strftime("%b %d %Y %H:%M:%S")
            }
            
            await self.bot.redis.set(f"case:{ctx.guild.id}:{case_id}", json.dumps(case_data))

            user_key = f"userlogs:{ctx.guild.id}:{user.id}"
            user_logs = await rget_json(self.bot, user_key) or []
            user_logs.append(case_id)
            await rset_json(self.bot, user_key, user_logs)

            return case_id
        except Exception as e:
            print(f"Modlog Save Error: {e}")
            return None

    # --- PREFIX MANAGEMENT ---
    @commands.hybrid_group(name="prefix", description="Manage command prefixes for this server.", invoke_without_command=True)
    async def prefix_group(self, ctx: commands.Context):
        """Default: List prefixes."""
        default_prefixes = ["!", ","]
        if not self.bot.redis:
            return await ctx.send(f"Memory offline. Currently using defaults: `{', '.join(default_prefixes)}`", ephemeral=True)
            
        try:
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            # Horizontal Sleek Display (Stellar HUD)
            prefix_line = " • ".join([f"`{p}`" for p in current_prefixes])
            embed = discord.Embed(title="Server Prefixes", description=f"{prefix_line}", color=0xB19CD9)
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"Error fetching prefixes: {e}")

    @prefix_group.command(name="add", description="Add a custom prefix for this server.")
    @commands.has_permissions(administrator=True)
    async def add_prefix(self, ctx: commands.Context, prefix: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        try:
            default_prefixes = ["!", ","]
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            normalized = [p.strip().lower() for p in current_prefixes]
            if prefix.strip().lower() in normalized:
                return await self._send_error(ctx, f"`{prefix}` is already a prefix (Normalization Conflict).")
            current_prefixes.append(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"Added `{prefix}` to prefixes.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to save prefix: {e}")

    @prefix_group.command(name="remove", description="Remove a prefix from this server.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix(self, ctx: commands.Context, prefix: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        try:
            default_prefixes = ["!", ","]
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            
            # Fuzzy Space Matching (Allows removing 'es' even if it's stored as 'es ')
            target = prefix.strip().lower()
            found_prefix = None
            for p in current_prefixes:
                if p.strip().lower() == target:
                    found_prefix = p
                    break
                    
            if not found_prefix:
                return await self._send_error(ctx, f"`{prefix}` isn't on the list.")
                
            if len(current_prefixes) <= 1:
                return await self._send_error(ctx, "Cannot remove the last prefix.")
                
            current_prefixes.remove(found_prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"Removed `{found_prefix}` from prefixes.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to remove prefix: {e}")

    # --- INFO GROUP ---
    @commands.hybrid_group(name="info", description="Retrieve detailed statistics and metadata.", invoke_without_command=True)
    async def info_group(self, ctx: commands.Context):
        """Default: Show Server Info."""
        await self.server_info(ctx)

    @info_group.command(name="server", description="Detailed statistics for this server.")
    async def server_info(self, ctx: commands.Context):
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"Info for {g.name}", color=0x3498db)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=f"{g.owner.mention if g.owner else 'Unknown'}", inline=True)
        embed.add_field(name="Members", value=f"Total: {g.member_count}\nHumans: {humans}\nBots: {bots}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.set_footer(text=f"ID: {g.id} | Created: {g.created_at.strftime('%d/%m/%Y')}")
        await ctx.send(embed=embed)

    @info_group.command(name="user", description="Detailed info about a member.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        bio = await rget(self.bot, f"bio:{user.id}") or "No bio set."
        embed = discord.Embed(title=f"{user.display_name}", description=f"*{bio}*", color=0xe74c3c)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y") if user.joined_at else "N/A", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        await ctx.send(embed=embed)

    @info_group.command(name="avatar", description="View a member's avatar.")
    async def avatar_info(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        embed = discord.Embed(title=f"Avatar for {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @info_group.command(name="members", description="See the breakdown of members.")
    async def members_info(self, ctx: commands.Context):
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"Member Count for {g.name}", color=0x2ecc71)
        embed.add_field(name="Total Members", value=f"**{g.member_count}**", inline=False)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        await ctx.send(embed=embed)

    # --- CASE GROUP ---
    @commands.hybrid_group(name="case", description="Manage administrative case logs.", invoke_without_command=True)
    async def case_group(self, ctx: commands.Context):
        """Default: Show usage."""
        await ctx.send_help(ctx.command)

    @case_group.command(name="view", description="View a user's entire case history.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_view(self, ctx: commands.Context, user: discord.User):
        user_key = f"userlogs:{ctx.guild.id}:{user.id}"
        case_ids = await rget_json(self.bot, user_key) or []
        if not case_ids:
            return await self._send_success(ctx, f"**{user.display_name}** has a clean record.")
        embed = discord.Embed(title=f"Modlogs for {user.display_name}", color=0x2b2d31)
        recent_cases = case_ids[-10:][::-1]
        description = ""
        for cid in recent_cases:
            case_data = await rget_json(self.bot, f"case:{ctx.guild.id}:{cid}")
            if case_data:
                description += f"**Case {case_data['id']}** | {case_data['type']}\nReason: {case_data['reason']} - *{case_data['date']}*\n\n"
        embed.description = description
        embed.set_footer(text=f"{len(case_ids)} total logs")
        await ctx.send(embed=embed)

    @case_group.command(name="edit", description="Change the reason for a specific case.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs_edit(self, ctx: commands.Context, case_id: int, *, new_reason: str):
        case_key = f"case:{ctx.guild.id}:{case_id}"
        case_data = await rget_json(self.bot, case_key)
        if not case_data:
            return await self._send_error(ctx, f"Case #{case_id} does not exist.")
        old_reason = case_data["reason"]
        case_data["reason"] = new_reason
        await rset_json(self.bot, case_key, case_data)
        await self._send_success(ctx, f"Updated Case #{case_id}\nOld: {old_reason}\nNew: {new_reason}")

    @case_group.command(name="clear", description="Wipe a user's entire case history.")
    @commands.has_permissions(administrator=True)
    async def modlogs_clear(self, ctx: commands.Context, user: discord.User):
        await self.bot.redis.delete(f"userlogs:{ctx.guild.id}:{user.id}")
        await self._send_success(ctx, f"Cleared logs for **{user.display_name}**.")

    # --- ROLE GROUP ---
    @commands.hybrid_group(name="role", description="Manage member roles.", invoke_without_command=True)
    async def role_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @role_group.command(name="add", description="Grant a role to a user.")
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await member.add_roles(role)
        await self._send_success(ctx, f"Granted **{role.name}** to {member.mention}.")

    @role_group.command(name="remove", description="Strip a role from a user.")
    @commands.has_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await member.remove_roles(role)
        await self._send_success(ctx, f"Stripped **{role.name}** from {member.mention}.")

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
            reply = await asyncio.to_thread(generate_reply, memory)
            embed = discord.Embed(description=reply[:4000], color=0x2b2d31)
            embed.set_author(name=f"💬 {prompt}"[:256])
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"System Error: {e}")

    @ai_group.command(name="lock", description="Lock Hyacine's AI to a specific channel.")
    @commands.has_permissions(administrator=True)
    async def ai_lock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        await self.bot.redis.set(f"chat_channel:{ctx.guild.id}", f"ID_{target.id}")
        await self._send_success(ctx, f"Neural link locked to {target.mention}.")

    @ai_group.command(name="unlock", description="Allow Hyacine to chat in all channels.")
    @commands.has_permissions(administrator=True)
    async def ai_unlock(self, ctx: commands.Context):
        await self.bot.redis.delete(f"chat_channel:{ctx.guild.id}")
        await self._send_success(ctx, "Channel lock removed.")

    # --- MODERATION (TOP LEVEL FOR SPEED) ---
    @commands.hybrid_command(name="warn", description="Issue a formal warning to a user.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        case_id = await self._log_case(ctx, "Warn", member, reason)
        await self._send_success(ctx, f"**{member.mention}** warned. Case #{case_id}", case_id=case_id)

    @commands.hybrid_command(name="mute", aliases=["timeout"], description="Mute a user.")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, user: discord.Member, minutes: int, *, reason: str = "No reason provided."):
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await rset_json(self.bot, f"mute:{ctx.guild.id}:{user.id}", {"until": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()})
        case_id = await self._log_case(ctx, "Mute", user, reason)
        await self._send_success(ctx, f"**{user.mention}** silenced for {minutes}m.", case_id=case_id)

    @commands.hybrid_command(name="unmute", description="Remove a user's mute early.")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None) 
        await self._send_success(ctx, f"**{member.mention}** has been unmuted.")

    @commands.hybrid_command(name="kick", description="Remove a weakling from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided."):
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await user.kick(reason=reason)
        case_id = await self._log_case(ctx, "Kick", user, reason)
        await self._send_success(ctx, f"**{user.mention}** ejected.", case_id=case_id)

    @commands.hybrid_command(name="ban", description="Permanently exile a user.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided."):
        member = ctx.guild.get_member(user.id)
        if member and member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await ctx.guild.ban(user, reason=reason)
        case_id = await self._log_case(ctx, "Ban", user, reason)
        await self._send_success(ctx, f"**{user.mention}** exiled.", case_id=case_id)

    # --- UTILITIES ---
    @commands.hybrid_command(name="ping", description="Check target response time.")
    async def ping(self, ctx: commands.Context):
        await self._send_success(ctx, f"Latencey: **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="uptime", description="Check system stability duration.")
    async def uptime(self, ctx: commands.Context):
        diff = datetime.now(timezone.utc) - self.start_time
        await self._send_success(ctx, f"Uptime: **{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m**")

    @commands.hybrid_command(name="purge", description="Purge messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        await ctx.defer(ephemeral=True)
        await ctx.channel.purge(limit=amount)
        await self._send_success(ctx, f"Purged {amount} messages.", ephemeral=True)

    @commands.hybrid_command(name="poll", description="Create a professional poll.")
    async def poll(self, ctx: commands.Context, question: str, *, options: str):
        opts = [o.strip() for o in options.split(",")]
        embed = discord.Embed(title=f"✧ {question}", description="\n\n".join([f"**{i+1}** {o}" for i,o in enumerate(opts)]), color=0x9B59B6)
        msg = await ctx.send(embed=embed)
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(len(opts)): await msg.add_reaction(emojis[i])

    @commands.hybrid_command(name="embed", description="Post a custom embed.")
    @commands.has_permissions(manage_messages=True)
    async def embed_cmd(self, ctx: commands.Context, title: str, description: str):
        embed = discord.Embed(title=f"✧ {title}", description=description, color=0x9B59B6)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setbio", description="Set your personal bio.")
    async def setbio(self, ctx: commands.Context, *, bio: str):
        await self.bot.redis.set(f"bio:{ctx.author.id}", bio[:150])
        await self._send_success(ctx, "Bio updated.", ephemeral=True)

async def setup(bot):
    if "StaffCommands" not in bot.cogs:
        await bot.add_cog(StaffCommands(bot))

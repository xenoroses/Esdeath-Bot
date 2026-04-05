import discord
from discord.ext import commands
import asyncio
import random
import time
import json
import math
from datetime import datetime, timedelta, timezone
import numexpr
from redis_utils import rget_json, rset_json, rget, rset, rdelete

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
        # Use a simple unique lock key based on context to prevent double-sends in rapid succession
        lock_key = f"lock:success:{ctx.author.id}:{getattr(ctx, 'command', 'cmd')}"
        if await self.bot.redis.set(lock_key, "1", nx=True, ex=1):
            embed = discord.Embed(description=f"✧ ✦ {text}", color=0x9B59B6)
            if case_id:
                embed.set_footer(text=f"𝒜𝓇𝒸𝒽i𝓋ℯ𝓁: 𝒞𝒶𝓈ℯ #{case_id}")
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
            prefix_line = " • ".join([f"`{p}`" for p in current_prefixes])
            embed = discord.Embed(title="𝒮ℯ𝓇𝓋ℯ𝓇 𝒫𝓇ℯ𝒻𝒾𝓍ℯ𝓈", description=f"{prefix_line}", color=0xB19CD9)
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"ℰ𝓇𝓇ℴ𝓇 𝒻ℯ𝓉𝒸𝒽𝒾𝓃𝑔 𝓅𝓇ℯ𝒻𝒾𝓍ℯ𝓈: {e}")

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
                return await self._send_error(ctx, f"`{prefix}` i𝓈 𝒶𝓁𝓇ℯ𝒶𝒹𝓎 𝒶 𝓅𝓇ℯ𝒻𝒾𝓍.")
            current_prefixes.append(prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"𝒜𝒹𝒹ℯ𝒹 `{prefix}` 𝓉ℴ 𝓅𝓇ℯ𝒻𝒾𝓍ℯ𝓈.")
        except Exception as e:
            await self._send_error(ctx, f"ℱ𝒶𝒾𝓁ℯ𝒹 𝓉ℴ 𝓈𝒶𝓋ℯ 𝓅𝓇ℯ𝒻𝒾𝓍: {e}")

    @prefix_group.command(name="remove", description="Remove a prefix from this server.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix(self, ctx: commands.Context, prefix: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        try:
            default_prefixes = ["!", ","]
            current_prefixes = await rget_json(self.bot, f"prefixes:{ctx.guild.id}") or default_prefixes
            
            target = prefix.strip().lower()
            found_prefix = None
            for p in current_prefixes:
                if p.strip().lower() == target:
                    found_prefix = p
                    break
                    
            if not found_prefix:
                return await self._send_error(ctx, f"`{prefix}` i𝓈𝓃'𝓉 ℴ𝓃 𝓉𝒽ℯ 𝓁𝒾𝓈𝓉.")
                
            if len(current_prefixes) <= 1:
                return await self._send_error(ctx, "𝒞𝒶𝓃𝓃ℴ𝓉 𝓇ℯ𝓂ℴ𝓋ℯ 𝓉𝒽ℯ 𝓁𝒶𝓈𝓉 𝓅𝓇ℯ𝒻𝒾𝓍.")
                
            current_prefixes.remove(found_prefix)
            await rset_json(self.bot, f"prefixes:{ctx.guild.id}", current_prefixes)
            await self._send_success(ctx, f"ℛℯ𝓂ℴ𝓋ℯ𝒹 `{found_prefix}` 𝒻𝓇ℴ𝓂 𝓅𝓇ℯ𝒻𝒾𝓍ℯ𝓈.")
        except Exception as e:
            await self._send_error(ctx, f"ℱ𝒶𝒾𝓁ℯ𝒹 𝓉ℴ 𝓇ℯ𝓂ℴ𝓋ℯ 𝓅𝓇ℯ𝒻𝒾𝓍: {e}")

    # --- INFO GROUP ---
    @commands.hybrid_group(name="info", description="Retrieve detailed statistics and metadata.", invoke_without_command=True)
    async def info_group(self, ctx: commands.Context):
        """Default: Show Server Info."""
        await self.server_info(ctx)

    @info_group.command(name="server", description="Detailed statistics for this server.")
    async def server_info(self, ctx: commands.Context):
        g = ctx.guild
        
        if g.member_count > 5000:
            bots_str = "Scale Optimized ⌬"
            humans_str = "Scale Optimized ⌬"
        else:
            bots = sum(1 for m in g.members if m.bot)
            humans = g.member_count - bots
            bots_str = str(bots)
            humans_str = str(humans)

        embed = discord.Embed(title=f"ℐ𝓃𝒻ℴ 𝒻ℴ𝓇 {g.name}", color=0x3498db)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=f"{g.owner.mention if g.owner else 'Unknown'}", inline=True)
        embed.add_field(name="Members", value=f"Total: {g.member_count}\nHumans: {humans_str}\nBots: {bots_str}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.set_footer(text=f"ID: {g.id} | Created: {g.created_at.strftime('%d/%m/%Y')}")
        await ctx.send(embed=embed)

    @info_group.command(name="user", description="Detailed info about a member.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        bio = await rget(self.bot, f"bio:{user.id}") or "No bio set."
        embed = discord.Embed(title=f"𝒰𝓈ℯ𝓇: {user.display_name}", description=f"*{bio}*", color=0xe74c3c)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y") if user.joined_at else "N/A", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setbio", description="Set your personal synaptic bio for info cards.")
    async def setbio(self, ctx: commands.Context, *, bio: str):
        if len(bio) > 200:
            return await self._send_error(ctx, "Bio must be under 200 characters.")
        await rset(self.bot, f"bio:{ctx.author.id}", bio)
        await self._send_success(ctx, "✧ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 ℬ𝒾ℴ 𝓅𝓊𝓇𝒾𝒻𝒾ℯ𝒹. Your identity has been updated.", ephemeral=True)

    @info_group.command(name="avatar", description="View a member's avatar.")
    async def avatar_info(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        embed = discord.Embed(title=f"𝒜𝓋𝒶𝓉𝒶𝓇 𝒻ℴ𝓇 {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

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
        embed = discord.Embed(title=f"ℳℴ𝒹𝓁ℴℊ𝓈 𝒻ℴ𝓇 {user.display_name}", color=0x2b2d31)
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
            return await self._send_error(ctx, f"𝒞𝒶𝓈ℯ #{case_id} 𝒹ℴℯ𝓈 𝓃ℴ𝓉 ℯ𝓍𝒾𝓈𝓉.")
        old_reason = case_data["reason"]
        case_data["reason"] = new_reason
        await rset_json(self.bot, case_key, case_data)
        await self._send_success(ctx, f"𝒰𝓅𝒹𝒶𝓉ℯ𝒹 𝒞𝒶𝓈ℯ #{case_id}\nOld: {old_reason}\nNew: {new_reason}")

    @case_group.command(name="clear", description="Wipe a user's entire case history.")
    @commands.has_permissions(administrator=True)
    async def modlogs_clear(self, ctx: commands.Context, user: discord.User):
        await rdelete(self.bot, f"userlogs:{ctx.guild.id}:{user.id}")
        await self._send_success(ctx, f"𝒞𝓁ℯ𝒶𝓇ℯ𝒹 𝓁ℴ𝑔𝓈 𝒻ℴ𝓇 **{user.display_name}**.")

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
        await self._send_success(ctx, f"𝒢𝓇𝒶𝓃𝓉ℯ𝒹 **{role.name}** 𝓉ℴ {member.mention}.")

    @role_group.command(name="remove", description="Strip a role from a user.")
    @commands.has_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await member.remove_roles(role)
        await self._send_success(ctx, f"𝒮𝓉𝓇𝒾𝓅𝓅ℯ𝒹 **{role.name}** 𝒻𝓇ℴ𝓂 {member.mention}.")

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
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: {e}")

    @ai_group.command(name="lock", description="Lock Hyacine's AI to a specific channel.")
    @commands.has_permissions(administrator=True)
    async def ai_lock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        await self.bot.redis.set(f"chat_channel:{ctx.guild.id}", f"ID_{target.id}")
        await self._send_success(ctx, f"𝒩ℯ𝓊𝓇𝒶𝓁 𝓁𝒾𝓃𝓀 𝓁ℴ𝒸𝓀ℯ𝒹 𝓉ℴ {target.mention}.")

    @ai_group.command(name="unlock", description="Allow Hyacine to chat in all channels.")
    @commands.has_permissions(administrator=True)
    async def ai_unlock(self, ctx: commands.Context):
        await self.bot.redis.delete(f"chat_channel:{ctx.guild.id}")
        await self._send_success(ctx, "𝒞𝒽𝒶𝓃𝓃ℯ𝓁 𝓁ℴ𝒸𝓀 𝓇ℯ𝓂ℴ𝓋ℯ𝒹.")

    # --- MODERATION (TOP LEVEL FOR SPEED) ---
    @commands.hybrid_command(name="warn", description="Issue a formal warning to a user.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        case_id = await self._log_case(ctx, "Warn", member, reason)
        await self._send_success(ctx, f"**{member.mention}** 𝓌𝒶𝓇𝓃ℯ𝒹. 𝒞𝒶𝓈ℯ #{case_id}", case_id=case_id)

    @commands.hybrid_command(name="mute", aliases=["timeout"], description="Mute a user.")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, user: discord.Member, minutes: int, *, reason: str = "No reason provided."):
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await rset_json(self.bot, f"mute:{ctx.guild.id}:{user.id}", {"until": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()})
        case_id = await self._log_case(ctx, "Mute", user, reason)
        await self._send_success(ctx, f"**{user.mention}** 𝓈𝒾𝓁ℯ𝓃𝒸ℯ𝒹 𝒻ℴ𝓇 {minutes}𝓂.", case_id=case_id)

    @commands.hybrid_command(name="unmute", description="Remove a user's mutes early.")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None) 
        await self._send_success(ctx, f"**{member.mention}** 𝒽𝒶𝓈 𝒷ℯℯ𝓃 𝓊𝓃𝓂𝓊𝓉ℯ𝒹.")

    @commands.hybrid_command(name="kick", description="Remove a weakling from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided."):
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await user.kick(reason=reason)
        case_id = await self._log_case(ctx, "Kick", user, reason)
        await self._send_success(ctx, f"**{user.mention}** ℯ𝒿ℯ𝒸𝓉ℯ𝒹.", case_id=case_id)

    @commands.hybrid_command(name="ban", description="Permanently exile a user.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided."):
        member = ctx.guild.get_member(user.id)
        if member and member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "Permission denied.")
        await ctx.guild.ban(user, reason=reason)
        case_id = await self._log_case(ctx, "Ban", user, reason)
        await self._send_success(ctx, f"**{user.mention}** ℯ𝓍𝒾𝓁ℯ𝒹.", case_id=case_id)

    # --- UTILITIES ---
    @commands.hybrid_command(name="ping", description="Check target response time.")
    async def ping(self, ctx: commands.Context):
        await self._send_success(ctx, f"ℒ𝒶𝓉ℯ𝓃𝒸𝓎: **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="uptime", description="Check system stability duration.")
    async def uptime(self, ctx: commands.Context):
        diff = datetime.now(timezone.utc) - self.start_time
        await self._send_success(ctx, f"𝒰𝓅𝓉𝒾𝓂ℯ: **{diff.days}𝒹 {diff.seconds//3600}𝒽 {(diff.seconds//60)%60}𝓂**")

    @commands.hybrid_command(name="purge", description="Purge messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        await ctx.defer(ephemeral=True)
        await ctx.channel.purge(limit=amount)
        await self._send_success(ctx, f"𝒫𝓊𝓇𝑔ℯ𝒹 {amount} 𝓂ℯ𝓈𝓈𝒶𝑔ℯ𝓈.", ephemeral=True)

    # --- SHADOWBAN (Migrated from Security) ---
    @commands.hybrid_command(name="shadowban", description="Invisible moderation: Auto-deletes all messages from a user silently.")
    @commands.has_permissions(ban_members=True)
    async def shadowban(self, ctx: commands.Context, user: discord.Member):
        # Hierarchy Validation
        if user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "𝒴ℴ𝓊 𝒸𝒶𝓃𝓃ℴ𝓉 𝓈𝒽𝒶𝒹ℴ𝓌ℬ𝒶𝓃 𝓉𝒽ℴ𝓈ℯ ℴ𝒻 ℯ𝓆𝓊𝒶𝓁 ℴ𝓇 𝒽𝒾ℊℯ𝓇 𝓇𝒶𝓃𝓀.")
        if user.top_role >= ctx.me.top_role:
            return await self._send_error(ctx, "𝒮𝒽𝒶𝒹ℴ𝓌ℬ𝒶𝓃 𝒻𝒶𝒾𝓁ℯ𝒹. 𝒮𝓊𝒷𝒿ℯ𝒸𝓉'𝓈 𝓃ℯ𝓊𝓇𝒶𝓁 𝓈ℋ𝒾ℯ𝓁𝒹𝒾𝓃ℊ (ℛℴ𝓁ℯ ℛ𝒶𝓃𝓀) 𝒾𝓈 𝒽𝒾ℊℯ𝓇 𝓉ℋ𝒶𝓃 𝓂𝒾𝓃ℯ.")

        key = f"shadowban:{ctx.guild.id}:{user.id}"
        
        if await rget(self.bot, key):
            await rdelete(self.bot, key)
            await self._send_success(ctx, f"𝒮𝒽𝒶𝒹ℴ𝓌ℬ𝒶𝓃 ℛℯ𝓁ℯ𝒶𝓈ℯ𝒹: {user.mention} has been restored to the visible plane.", ephemeral=True)
        else:
            value = str(int(time.time()))
            await rset(self.bot, key, value)
            await self._send_success(ctx, f"{user.mention} is now **shadowbanned**. All future transmissions will vanish into the void.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Shadowban Execution
        if not self.bot.redis: return
        sb_key = f"shadowban:{message.guild.id}:{message.author.id}"
        if await rget(self.bot, sb_key):
            try:
                await message.delete()
            except: pass

async def setup(bot):
    if "Staff" not in bot.cogs:
        await bot.add_cog(StaffCommands(bot))

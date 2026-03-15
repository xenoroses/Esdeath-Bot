import discord
from discord.ext import commands
import asyncio
import random
import requests
import time
import json
import math
from datetime import datetime, timedelta

# --- INTERACTIVE HELP PAGINATOR ---
class HelpPaginator(discord.ui.View):
    def __init__(self, ctx, cmds):
        super().__init__(timeout=180) 
        self.ctx = ctx
        self.cmds = cmds
        self.current_page = 1
        self.per_page = 5 
        self.total_pages = max(1, math.ceil(len(self.cmds) / self.per_page))

        self.first_btn = discord.ui.Button(label="FIRST", style=discord.ButtonStyle.success, custom_id="first")
        self.first_btn.callback = self.first_page
        self.add_item(self.first_btn)

        self.prev_btn = discord.ui.Button(label="PREVIOUS", style=discord.ButtonStyle.secondary, custom_id="prev")
        self.prev_btn.callback = self.previous_page
        self.add_item(self.prev_btn)

        self.counter_btn = discord.ui.Button(label=f"1/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True, custom_id="counter")
        self.add_item(self.counter_btn)

        self.next_btn = discord.ui.Button(label="NEXT", style=discord.ButtonStyle.success, custom_id="next")
        self.next_btn.callback = self.next_page
        self.add_item(self.next_btn)

        self.last_btn = discord.ui.Button(label="LAST", style=discord.ButtonStyle.success, custom_id="last")
        self.last_btn.callback = self.last_page
        self.add_item(self.last_btn)
        
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't your menu. Run the command yourself.", ephemeral=True)
            return False
        return True

    def update_buttons(self):
        self.first_btn.disabled = self.current_page == 1
        self.prev_btn.disabled = self.current_page == 1
        self.next_btn.disabled = self.current_page == self.total_pages
        self.last_btn.disabled = self.current_page == self.total_pages
        self.counter_btn.label = f"{self.current_page}/{self.total_pages}"

    def get_embed(self):
        embed = discord.Embed(title="Help", color=0x2ecc71) 
        description = ""
        
        if self.current_page == 1:
            description += "**SOME HELPFUL LINKS-**\n"
            description += "[Dashboard](https://huggingface.co/spaces/xenoroses/Esdeath-Bot)\n"
            description += "[Bot support server](https://discord.gg/yourserver)\n\n"
            description += "**HELP COMMANDS -**\n\n"
        else:
            description += "**HELP COMMANDS -**\n\n"

        start_idx = (self.current_page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        page_cmds = self.cmds[start_idx:end_idx]

        for cmd_name, cmd_desc in page_cmds:
            description += f"**{self.ctx.clean_prefix}{cmd_name}**\n{cmd_desc}\n\n"
            
        embed.description = description
        return embed

    async def update_page(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def first_page(self, interaction: discord.Interaction):
        self.current_page = 1
        await self.update_page(interaction)

    async def previous_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        await self.update_page(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        await self.update_page(interaction)

    async def last_page(self, interaction: discord.Interaction):
        self.current_page = self.total_pages
        await self.update_page(interaction)


class StaffCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    # --- INTERNAL HELPERS ---
    async def _send_error(self, ctx, text):
        """Sends a sleek, dark-mode error notification (Always Ephemeral)."""
        embed = discord.Embed(description=f"❌ | {text}", color=0x2b2d31)
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_success(self, ctx, text, ephemeral=False):
        """Carl-bot style precision success embed."""
        embed = discord.Embed(description=f"✅ | {text}", color=0x2ecc71)
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
                "date": datetime.utcnow().strftime("%b %d %Y %H:%M:%S")
            }
            
            await self.bot.redis.set(f"case:{ctx.guild.id}:{case_id}", json.dumps(case_data))
            
            user_key = f"userlogs:{ctx.guild.id}:{user.id}"
            cached = await self.bot.redis.get(user_key)
            user_logs = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached) if cached else []
            user_logs.append(case_id)
            await self.bot.redis.set(user_key, json.dumps(user_logs))
            
            return case_id
        except Exception as e:
            print(f"Modlog Save Error: {e}")
            return None

    # --- DYNAMIC HELP ---
    @commands.hybrid_command(name="help", description="Displays the interactive command guide.")
    async def help_command(self, ctx: commands.Context):
        cmds = []
        for command in self.bot.commands:
            if not command.hidden:
                cmds.append((command.name, command.description or "No description provided."))
        
        cmds.sort(key=lambda x: x[0])
        
        if not cmds:
            return await self._send_error(ctx, "I have no commands configured yet.")
            
        view = HelpPaginator(ctx, cmds)
        await ctx.send(embed=view.get_embed(), view=view)

    # --- PREFIX MANAGEMENT ---
    @commands.hybrid_command(name="prefixes", description="See all active prefixes for this server.")
    async def prefixes(self, ctx: commands.Context):
        default_prefixes = ["!", "esdeath ", "es "]
        if not self.bot.redis:
            return await ctx.send(f"Memory offline. Currently using defaults: `{', '.join(default_prefixes)}`", ephemeral=True)
            
        try:
            cached = await self.bot.redis.get(f"prefixes:{ctx.guild.id}")
            current_prefixes = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached) if cached else default_prefixes
            
            embed = discord.Embed(title="Server Prefixes", description="\n".join([f"• `{p}`" for p in current_prefixes]), color=0x3498db)
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"Error fetching prefixes: {e}")

    @commands.hybrid_command(name="addprefix", description="Add a custom prefix for this server.")
    @commands.has_permissions(administrator=True)
    async def addprefix(self, ctx: commands.Context, prefix: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "My memory banks are offline. Try again later.")
            
        try:
            cached = await self.bot.redis.get(f"prefixes:{ctx.guild.id}")
            current_prefixes = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached) if cached else ["!", "esdeath ", "es "]
            
            if prefix in current_prefixes:
                return await self._send_error(ctx, f"`{prefix}` is already a prefix here.")
                
            current_prefixes.append(prefix)
            await self.bot.redis.set(f"prefixes:{ctx.guild.id}", json.dumps(current_prefixes))
            await self._send_success(ctx, f"Added `{prefix}` to this server's prefixes.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to save prefix: {e}")

    @commands.hybrid_command(name="removeprefix", description="Remove a prefix from this server.")
    @commands.has_permissions(administrator=True)
    async def removeprefix(self, ctx: commands.Context, prefix: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "My memory banks are offline. Try again later.")
            
        try:
            cached = await self.bot.redis.get(f"prefixes:{ctx.guild.id}")
            current_prefixes = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached) if cached else ["!", "esdeath ", "es "]
            
            if prefix not in current_prefixes:
                return await self._send_error(ctx, f"`{prefix}` isn't on the prefix list.")
            
            if len(current_prefixes) <= 1:
                return await self._send_error(ctx, "You can't remove the last prefix! How would you command me?")
                
            current_prefixes.remove(prefix)
            await self.bot.redis.set(f"prefixes:{ctx.guild.id}", json.dumps(current_prefixes))
            await self._send_success(ctx, f"Removed `{prefix}` from this server's prefixes.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to remove prefix: {e}")

    # --- BATCH 1: IDENTITY & INFO ---
    @commands.hybrid_command(name="serverinfo", description="Detailed statistics for this server.")
    async def serverinfo(self, ctx: commands.Context):
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

    @commands.hybrid_command(name="userinfo", description="Detailed info about a member, including their bio.")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        
        bio = "No bio set. How boring."
        if self.bot.redis:
            try:
                fetched_bio = await self.bot.redis.get(f"bio:{user.id}")
                if fetched_bio:
                    bio = fetched_bio.decode('utf-8') if isinstance(fetched_bio, bytes) else fetched_bio
            except Exception:
                pass 

        embed = discord.Embed(title=f"{user.display_name}", description=f"*{bio}*", color=0xe74c3c)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y") if user.joined_at else "N/A", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="View a member's avatar.")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        embed = discord.Embed(title=f"Avatar for {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Check the bot's response time.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await self._send_success(ctx, f"It took me **{latency}ms** to notice you. Don't make me wait longer next time.")

    @commands.hybrid_command(name="uptime", description="Check how long the bot has been online.")
    async def uptime(self, ctx: commands.Context):
        uptime_diff = datetime.utcnow() - self.start_time
        days = uptime_diff.days
        hours, remainder = divmod(uptime_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await self._send_success(ctx, f"I have been standing guard for **{days}d, {hours}h, {minutes}m, {seconds}s**.")

    @commands.hybrid_command(name="echo", description="Make Esdeath say something.")
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx: commands.Context, *, message: str):
        await ctx.channel.send(message)
        await self._send_success(ctx, "Message delivered.", ephemeral=True)

    @commands.hybrid_command(name="fancy", description="Convert text into 𝒻𝒶𝓃𝒸𝓎 𝓈𝒸𝓇𝒾𝓅𝓉.")
    async def fancy(self, ctx: commands.Context, *, text: str):
        mapping = str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
        )
        await ctx.send(text.translate(mapping))

    # --- BATCH 2: MODERATION & CASE LOGGING ---
    @commands.hybrid_command(name="warn", description="Issue a formal warning to a user.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "You cannot warn your superiors.")
        
        case_id = await self._log_case(ctx, "Warn", member, reason)
        case_txt = f" *(Case #{case_id})*" if case_id else ""
        
        await self._send_success(ctx, f"**{member.mention}** has been formally warned.{case_txt}\nReason: `{reason}`")
        try:
            await member.send(f"You were warned in **{ctx.guild.name}**. Reason: `{reason}`")
        except: pass

    @commands.hybrid_command(name="mute", aliases=["timeout"], description="Mute a user (Timeout).")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided."):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "I won't silence my superiors.")
        try:
            duration = timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            case_id = await self._log_case(ctx, "Mute", member, reason)
            case_txt = f" *(Case #{case_id})*" if case_id else ""
            await self._send_success(ctx, f"**{member.mention}** has been silenced for {minutes} minutes.{case_txt}")
        except discord.Forbidden:
            await self._send_error(ctx, "My role isn't high enough to mute them.")

    @commands.hybrid_command(name="unmute", description="Remove a user's mute early.")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        try:
            await member.timeout(None) 
            await self._send_success(ctx, f"**{member.mention}** has been unmuted. Don't make me regret it.")
        except discord.Forbidden:
            return await self._send_error(ctx, "I lack permissions to unmute them.")

    @commands.hybrid_command(name="kick", description="Remove a weakling from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "You don't have the authority to remove someone stronger than you.")
        try:
            await member.kick(reason=reason)
            case_id = await self._log_case(ctx, "Kick", member, reason)
            case_txt = f" *(Case #{case_id})*" if case_id else ""
            await self._send_success(ctx, f"**{member.mention}** has been removed.{case_txt} I have no use for the weak.")
        except discord.Forbidden:
            return await self._send_error(ctx, "I lack the 'Kick Members' permission.")

    @commands.hybrid_command(name="ban", description="Permanently exile a user by tag or ID.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided."):
        member = ctx.guild.get_member(user.id)
        if member and member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "I cannot exile someone of that rank.")
        try:
            await ctx.guild.ban(user, reason=reason)
            case_id = await self._log_case(ctx, "Ban", user, reason)
            case_txt = f" *(Case #{case_id})*" if case_id else ""
            await self._send_success(ctx, f"**{user.mention}** has been exiled.{case_txt} Don't bother coming back.")
        except discord.Forbidden:
            return await self._send_error(ctx, "I lack the 'Ban Members' permission, or my role is lower than theirs.")

    # --- BATCH 2.5: MODLOG MANAGEMENT (CARL/DYNO STYLE) ---
    @commands.hybrid_command(name="modlogs", aliases=["ml", "logs"], description="View a user's entire case history.")
    @commands.has_permissions(moderate_members=True)
    async def modlogs(self, ctx: commands.Context, user: discord.User):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
            
        user_key = f"userlogs:{ctx.guild.id}:{user.id}"
        cached = await self.bot.redis.get(user_key)
        case_ids = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached) if cached else []
        
        if not case_ids:
            return await self._send_success(ctx, f"**{user.display_name}** has a clean record. For now.")
            
        embed = discord.Embed(title=f"Modlogs for {user.display_name}", color=0x2b2d31)
        
        recent_cases = case_ids[-10:] 
        recent_cases.reverse() 
        
        description = ""
        for cid in recent_cases:
            case_raw = await self.bot.redis.get(f"case:{ctx.guild.id}:{cid}")
            if case_raw:
                c = json.loads(case_raw.decode('utf-8') if isinstance(case_raw, bytes) else case_raw)
                description += f"**Case {c['id']}** | {c['type']}\n"
                description += f"**User:** {c['user_name']} ({c['user_id']})\n"
                description += f"**Moderator:** {c['mod_name']}\n"
                description += f"**Reason:** {c['reason']} - *{c['date']}*\n\n"
                
        embed.description = description
        embed.set_footer(text=f"{len(case_ids)} total logs | Showing recent {len(recent_cases)}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="reason", aliases=["editcase"], description="Change the reason for a specific case.")
    @commands.has_permissions(moderate_members=True)
    async def reason(self, ctx: commands.Context, case_id: int, *, new_reason: str):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
            
        case_key = f"case:{ctx.guild.id}:{case_id}"
        cached = await self.bot.redis.get(case_key)
        
        if not cached:
            return await self._send_error(ctx, f"Case #{case_id} does not exist.")
            
        case_data = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached)
        old_reason = case_data["reason"]
        case_data["reason"] = new_reason
        
        if case_data["type"] == "Ban":
            try:
                user = await self.bot.fetch_user(case_data["user_id"])
                await ctx.guild.fetch_ban(user)
                await ctx.guild.ban(user, reason=new_reason)
            except: pass 

        await self.bot.redis.set(case_key, json.dumps(case_data))
        await self._send_success(ctx, f"Updated **Case #{case_id}**\n**Old:** {old_reason}\n**New:** {new_reason}")

    @commands.hybrid_command(name="clearwarns", description="Wipe a user's entire case history.")
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx: commands.Context, user: discord.User):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        await self.bot.redis.delete(f"userlogs:{ctx.guild.id}:{user.id}")
        await self._send_success(ctx, f"Cleared all modlogs for **{user.display_name}**.")

    @commands.hybrid_command(name="purge", description="Delete a specific amount of messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        if amount > 100:
            return await self._send_error(ctx, "I'm not cleaning up more than 100 messages at once.")
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await self._send_success(ctx, f"I've vaporized {len(deleted)} messages. The chat is clean now.", ephemeral=True)

    @commands.hybrid_command(name="slowmode", description="Set the channel's slowmode delay.")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await self._send_success(ctx, "Slowmode has been disabled. Talk as much as you want.")
        else:
            await self._send_success(ctx, f"Slowmode set to {seconds} seconds. Think before you speak.")

    # --- BATCH 3: INTERACTIVE TOOLS ---
    @commands.hybrid_command(name="poll", description="Create a professional poll.")
    async def poll(self, ctx: commands.Context, question: str, *, options: str):
        option_list = [opt.strip() for opt in options.split(",")]
        if len(option_list) > 10:
            return await self._send_error(ctx, "I'm not counting more than 10 options. Keep it simple.")
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        description = ""
        for i, option in enumerate(option_list):
            description += f"{emojis[i]} {option}\n\n"
            
        embed = discord.Embed(title=f"📊 {question}", description=description, color=0x3498db)
        embed.set_footer(text=f"Poll started by {ctx.author.display_name}")
        
        poll_msg = await ctx.send(embed=embed)
        for i in range(len(option_list)):
            await poll_msg.add_reaction(emojis[i])

    @commands.hybrid_command(name="embed", description="Make Esdeath post a custom colored box.")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx: commands.Context, title: str, description: str, color: str = "blue"):
        color_map = {"blue": 0x3498db, "red": 0xe74c3c, "green": 0x2ecc71, "gold": 0xf1c40f}
        hex_color = color_map.get(color.lower(), 0x3498db)
        
        custom_embed = discord.Embed(title=title, description=description, color=hex_color)
        custom_embed.set_footer(text=f"Official Notice from {ctx.guild.name}")
        
        await self._send_success(ctx, "Embed deployed.", ephemeral=True)
        await ctx.channel.send(embed=custom_embed)

    @commands.hybrid_command(name="remind", description="Set a personal reminder.")
    async def remind(self, ctx: commands.Context, minutes: int, *, note: str):
        await self._send_success(ctx, f"Fine. I'll remind you about '{note}' in {minutes} minutes.", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try:
            await ctx.author.send(f"Hey. You told me to remind you: **{note}**")
        except:
            await ctx.channel.send(f"{ctx.author.mention}, listen up. You wanted to be reminded: **{note}**")

    # --- BATCH 4: ADVANCED UTILITY & FUN ---
    @commands.hybrid_command(name="urban", description="Look up a term on Urban Dictionary.")
    async def urban(self, ctx: commands.Context, *, term: str):
        url = f"https://api.urbandictionary.com/v0/define?term={term}"
        response = requests.get(url).json()
        
        if not response['list']:
            return await self._send_error(ctx, f"Even the internet doesn't know what '{term}' means. How pathetic.")
        
        first_entry = response['list'][0]
        definition = first_entry['definition']
        
        embed = discord.Embed(description=f"{definition[:2000]}", color=0x2b2d31)
        embed.set_author(name=f"Definition of '{term}'", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"👍 {first_entry['thumbs_up']} | 👎 {first_entry['thumbs_down']}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="math", description="Solve a basic math problem.")
    async def math(self, ctx: commands.Context, *, expression: str):
        try:
            allowed = "0123456789+-*/(). "
            if all(c in allowed for c in expression):
                result = eval(expression)
                await self._send_success(ctx, f"The answer is **{result}**. Honestly, you couldn't solve that yourself?")
            else:
                return await self._send_error(ctx, "Don't try to hack me with your weird symbols.")
        except:
            return await self._send_error(ctx, "That's not even a valid equation.")

    @commands.hybrid_command(name="roll", description="Roll some dice (e.g., 2d6).")
    async def roll(self, ctx: commands.Context, dice: str = "1d6"):
        try:
            amount, sides = map(int, dice.lower().split('d'))
            if amount > 100 or sides > 1000:
                return await self._send_error(ctx, "I'm not rolling that many dice. Stop being extra.")
            
            rolls = [random.randint(1, sides) for _ in range(amount)]
            total = sum(rolls)
            await self._send_success(ctx, f"Rolling **{dice}**... You got: `{rolls}` (Total: **{total}**)")
        except:
            return await self._send_error(ctx, "Format it correctly, like `2d20`.")

    @commands.hybrid_command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, ctx: commands.Context):
        result = random.choice(["Heads", "Tails"])
        await self._send_success(ctx, f"The coin landed on... **{result}**.")

    @commands.hybrid_command(name="membercount", description="See the breakdown of members.")
    async def membercount(self, ctx: commands.Context):
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        
        embed = discord.Embed(title=f"Member Count for {g.name}", color=0x2ecc71)
        embed.add_field(name="Total Members", value=f"**{g.member_count}**", inline=False)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        await ctx.send(embed=embed)

    # --- BATCH 5: ROLE MANAGEMENT & PROFILES ---
    @commands.hybrid_command(name="addrole", description="Grant a role to a user.")
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "You can't give a role that is equal to or higher than your own.")
        try:
            await member.add_roles(role)
            await self._send_success(ctx, f"Granted **{role.name}** to {member.mention}. Try to be worthy of it.")
        except discord.Forbidden:
            return await self._send_error(ctx, "My role isn't high enough! Drag the 'Esdeath' role HIGHER in Server Settings.")

    @commands.hybrid_command(name="removerole", description="Strip a role from a user.")
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "You don't have the authority to strip this role.")
        try:
            await member.remove_roles(role)
            await self._send_success(ctx, f"Stripped **{role.name}** from {member.mention}. Back to the bottom you go.")
        except discord.Forbidden:
            return await self._send_error(ctx, "I cannot strip this role because it is higher than my own.")

    @commands.hybrid_command(name="nickname", description="Force a new nickname on a user.")
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx: commands.Context, member: discord.Member, *, new_name: str):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await self._send_error(ctx, "I don't take orders to rename my superiors.")
        try:
            old_name = member.display_name
            await member.edit(nick=new_name)
            await self._send_success(ctx, f"Renamed **{old_name}** to **{new_name}**. Learn to live with it.")
        except discord.Forbidden:
            return await self._send_error(ctx, "I cannot rename this user because their role is higher than mine.")

    @commands.hybrid_command(name="setbio", description="Set your personal profile bio.")
    async def setbio(self, ctx: commands.Context, *, bio: str):
        if len(bio) > 150:
            return await self._send_error(ctx, "Keep it under 150 characters. I don't want to read an essay.")
        if not self.bot.redis:
            return await self._send_error(ctx, "My memory banks are currently offline. Try again later.")
            
        await self.bot.redis.set(f"bio:{ctx.author.id}", bio)
        await self._send_success(ctx, "Bio updated. I'll make sure everyone sees it.", ephemeral=True)    

    @commands.hybrid_command(name="ask", description="Consult the Advanced AI Assistant.")
    async def ask(self, ctx: commands.Context, *, prompt: str):
        await ctx.defer()
        try:
            from llm import generate_reply
            import asyncio
            
            system_prompt = (
                "You are a highly intelligent, helpful, and official AI assistant. "
                "Provide clear, accurate, and engaging answers. "
                "Always use Discord Markdown formatting (like **bolding** key terms, using bullet points, and short paragraphs) to make your response extremely easy to read."
            )
            
            memory = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            reply = await asyncio.to_thread(generate_reply, memory)
            if len(reply) > 4096:
                reply = reply[:4093] + "..."
            
            embed = discord.Embed(description=reply, color=0x2b2d31)
            embed.set_author(name=f"💬 {prompt}"[:256], icon_url=ctx.author.display_avatar.url)
            embed.set_footer(
                text="Advanced AI System • Esdeath Network", 
                icon_url="https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg" 
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await self._send_error(ctx, f"System Error: {e}")

    # --- AI CHAT CHANNEL CONFIGURATION ---
    @commands.hybrid_command(name="setchat", description="Lock Esdeath's AI responses to a specific channel.")
    @commands.has_permissions(administrator=True)
    async def setchat(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not getattr(self.bot, 'redis', None):
            return await self._send_error(ctx, "Memory offline. Cannot save channel lock.")
        
        target_channel = channel or ctx.channel
        
        # THE FIX: Wrap target_channel.id in str() so the database doesn't round the massive number
        await self.bot.redis.set(f"chat_channel:{ctx.guild.id}", str(target_channel.id))
        
        await self._send_success(ctx, f"Neural link locked to {target_channel.mention}. AI chat is restricted to this channel.")

    @commands.hybrid_command(name="clearchat", description="Allow Esdeath to chat in all channels again.")
    @commands.has_permissions(administrator=True)
    async def clearchat(self, ctx: commands.Context):
        if not self.bot.redis:
            return await self._send_error(ctx, "Memory offline.")
        
        await self.bot.redis.delete(f"chat_channel:{ctx.guild.id}")
        await self._send_success(ctx, "Channel lock removed. Esdeath can now be summoned globally.")
            

# --- GLOBAL SETUP FUNCTION ---
async def setup(bot):
    await bot.add_cog(StaffCommands(bot))
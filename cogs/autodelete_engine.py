import discord
from discord.ext import commands, tasks
import json
import re
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Literal
from redis_utils import rget_json, rset_json

def parse_duration_to_seconds(duration_str: str) -> Optional[int]:
    """
    Parses human readable duration string into seconds.
    Examples: '5m' -> 300, '1h' -> 3600, '1d' -> 86400, '1w' -> 604800, '0' -> 0.
    """
    duration_str = str(duration_str).strip().lower()
    if duration_str in ["0", "instant", "now", "off"]:
        return 0
    match = re.match(r"^(\d+)\s*([smhdw]?)$", duration_str)
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if not unit or unit == "s":
        return val
    elif unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    elif unit == "d":
        return val * 86400
    elif unit == "w":
        return val * 604800
    return None

def format_seconds_to_duration(seconds: int) -> str:
    if seconds == 0:
        return "Instant (On Send)"
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''}"
    elif seconds < 86400:
        hrs = seconds // 3600
        return f"{hrs} hour{'s' if hrs > 1 else ''}"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''}"
    else:
        weeks = seconds // 604800
        return f"{weeks} week{'s' if weeks > 1 else ''}"

class AutoDeleteEngine(commands.Cog):
    """
    Tier 3 Platform Feature: Advanced EazyAutodelete Engine.
    High-performance, multi-filter, custom-duration message autodelete system.
    """
    def __init__(self, bot):
        self.bot = bot
        self.autodelete_loop.start()

    def cog_unload(self):
        self.autodelete_loop.cancel()

    async def _send_embed(
        self, 
        dest: Union[discord.abc.Messageable, commands.Context], 
        embed: discord.Embed, 
        ephemeral: bool = False, 
        fallback_text: Optional[str] = None
    ):
        """Standardized robust response handler for all cogs."""
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

    async def get_channel_config(self, guild_id: int, channel_id: int) -> dict:
        key = f"autodelete:config:{guild_id}:{channel_id}"
        config = await rget_json(self.bot, key)
        if not config:
            return {
                "enabled": False,
                "duration_seconds": 300, # Default 5 mins
                "filter_mode": "all",    # all, links, media, text, bots, humans, mentions, contains, not_contains
                "specific_text": None,
                "exempt_pinned": True,
                "exempt_bots": False,
                "exempt_admins": True,
                "exempt_roles": [],
                "target_roles": [],
                "exempt_users": [],
                "target_users": [],
                "log_channel_id": None
            }
        return config

    async def save_channel_config(self, guild_id: int, channel_id: int, config: dict):
        key = f"autodelete:config:{guild_id}:{channel_id}"
        await rset_json(self.bot, key, config)
        
        # Update guild registry set
        reg_key = f"autodelete:channels:{guild_id}"
        channels = await rget_json(self.bot, reg_key) or []
        if config.get("enabled") and channel_id not in channels:
            channels.append(channel_id)
            await rset_json(self.bot, reg_key, channels)
        elif not config.get("enabled") and channel_id in channels:
            channels.remove(channel_id)
            await rset_json(self.bot, reg_key, channels)

    def should_delete_message(self, message: discord.Message, config: dict) -> bool:
        if not config.get("enabled"):
            return False

        # Pinned Check
        if config.get("exempt_pinned", True) and message.pinned:
            return False

        # Bot Check
        if message.author.bot:
            if config.get("exempt_bots", False):
                return False
        else:
            # Admin check for humans
            if config.get("exempt_admins", True) and isinstance(message.author, discord.Member):
                if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_guild:
                    return False

        # Member Role / User checks
        if isinstance(message.author, discord.Member):
            user_roles = [r.id for r in message.author.roles]
            # Role exemption
            if any(rid in config.get("exempt_roles", []) for rid in user_roles):
                return False
            # Target roles filter
            target_roles = config.get("target_roles", [])
            if target_roles and not any(rid in target_roles for rid in user_roles):
                return False

        # User ID checks
        if message.author.id in config.get("exempt_users", []):
            return False
        target_users = config.get("target_users", [])
        if target_users and message.author.id not in target_users:
            return False

        # Content Filter Checks
        fmode = config.get("filter_mode", "all")
        content = message.content or ""
        
        if fmode == "all":
            return True
        elif fmode == "links":
            return bool(re.search(r"http[s]?://", content))
        elif fmode == "media":
            return len(message.attachments) > 0 or len(message.embeds) > 0
        elif fmode == "text":
            return len(message.attachments) == 0 and len(message.embeds) == 0 and not bool(re.search(r"http[s]?://", content))
        elif fmode == "bots":
            return message.author.bot
        elif fmode == "humans":
            return not message.author.bot
        elif fmode == "mentions":
            return bool(message.mentions or message.role_mentions or message.mention_everyone)
        elif fmode == "contains":
            stext = config.get("specific_text")
            return bool(stext and stext.lower() in content.lower())
        elif fmode == "not_contains":
            stext = config.get("specific_text")
            return bool(stext and stext.lower() not in content.lower())

        return True

    @commands.hybrid_group(name="autodelete", aliases=["autoclean", "ad"], description="Advanced customizable message auto-delete engine.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autodelete_group.command(name="setup", description="Quickly setup auto-delete for a channel.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_setup(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        duration: str = "1h",
        filter_mode: Literal["all", "links", "media", "text", "bots", "humans", "mentions"] = "all",
        exempt_pinned: bool = True
    ):
        await ctx.defer()
        ch = channel or ctx.channel
        sec = parse_duration_to_seconds(duration)
        if sec is None:
            return await ctx.send("❌ **Invalid duration format.** Use e.g. `5m`, `1h`, `24h`, `1d`, `7d`, or `0` for instant.", ephemeral=True)

        config = await self.get_channel_config(ctx.guild.id, ch.id)
        config["enabled"] = True
        config["duration_seconds"] = sec
        config["filter_mode"] = filter_mode
        config["exempt_pinned"] = exempt_pinned

        await self.save_channel_config(ctx.guild.id, ch.id, config)

        dur_text = format_seconds_to_duration(sec)
        embed = discord.Embed(
            title="⚙️ 𝒜𝓊𝓉ℴ𝒟ℯ𝓁ℯ𝓉ℯ 𝒞ℴ𝓃𝒻𝒾𝑔𝓊𝓇ℯ𝒹",
            description=f"Auto-delete successfully activated for {ch.mention}.\n\n"
                        f"• **Duration / Interval**: `{dur_text}`\n"
                        f"• **Content Filter**: `{filter_mode}`\n"
                        f"• **Exempt Pinned**: `{'Yes' if exempt_pinned else 'No'}`",
            color=0x2ECC71
        )
        embed.set_footer(text="Engine: Hyacine EazyAutodelete Architecture")
        await self._send_embed(ctx, embed, fallback_text=f"Auto-delete configured for {ch.name}.")

    @autodelete_group.command(name="config", description="Display auto-delete configuration for a channel.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_config(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await ctx.defer()
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        status = "Active ✧" if config.get("enabled") else "Disabled ⌬"
        dur_text = format_seconds_to_duration(config.get("duration_seconds", 300))

        exempt_roles = [f"<@&{rid}>" for rid in config.get("exempt_roles", [])]
        target_roles = [f"<@&{rid}>" for rid in config.get("target_roles", [])]
        log_ch = f"<#{config.get('log_channel_id')}>" if config.get("log_channel_id") else "None"

        embed = discord.Embed(
            title=f"🛠️ 𝒜𝓊𝓉ℴ𝒟ℯ𝓁ℯ𝓉ℯ 𝒮𝓅ℯ𝒸𝒾𝒻𝒾𝒸𝒶𝓉𝒾ℴ𝓃 — #{ch.name}",
            color=0x3498DB
        )
        embed.add_field(name="Status", value=f"**{status}**", inline=True)
        embed.add_field(name="Duration", value=f"`{dur_text}`", inline=True)
        embed.add_field(name="Filter Mode", value=f"`{config.get('filter_mode', 'all')}`", inline=True)

        if config.get("specific_text"):
            embed.add_field(name="Target Query Text", value=f"`{config.get('specific_text')}`", inline=False)

        embed.add_field(name="Exempt Pinned", value=f"`{config.get('exempt_pinned', True)}`", inline=True)
        embed.add_field(name="Exempt Bots", value=f"`{config.get('exempt_bots', False)}`", inline=True)
        embed.add_field(name="Exempt Admins", value=f"`{config.get('exempt_admins', True)}`", inline=True)

        embed.add_field(name="Exempt Roles", value=", ".join(exempt_roles) if exempt_roles else "*None*", inline=False)
        embed.add_field(name="Target Roles Only", value=", ".join(target_roles) if target_roles else "*All Roles*", inline=False)
        embed.add_field(name="Log Channel", value=log_ch, inline=True)

        embed.set_footer(text="Use /autodelete options or /autodelete roles to customize.")
        await self._send_embed(ctx, embed, fallback_text=f"AutoDelete Config for #{ch.name}: {status}, {dur_text}.")

    @autodelete_group.command(name="duration", description="Set deletion delay interval (e.g. 5m, 1h, 1d, 7d).")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_duration(self, ctx: commands.Context, duration: str, channel: Optional[discord.TextChannel] = None):
        await ctx.defer()
        ch = channel or ctx.channel
        sec = parse_duration_to_seconds(duration)
        if sec is None:
            return await ctx.send("❌ **Invalid duration format.** Use e.g. `5m`, `15m`, `1h`, `24h`, `1d`, `7d`, or `0`.", ephemeral=True)

        config = await self.get_channel_config(ctx.guild.id, ch.id)
        config["duration_seconds"] = sec
        config["enabled"] = True
        await self.save_channel_config(ctx.guild.id, ch.id, config)

        dur_text = format_seconds_to_duration(sec)
        await ctx.send(f"✧ **Auto-delete interval for {ch.mention} set to:** `{dur_text}`.")

    @autodelete_group.command(name="filter", description="Set content filter mode for channel auto-deletion.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_filter(
        self, 
        ctx: commands.Context, 
        mode: Literal["all", "links", "media", "text", "bots", "humans", "mentions", "contains", "not_contains"],
        specific_text: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        await ctx.defer()
        ch = channel or ctx.channel

        if mode in ["contains", "not_contains"] and not specific_text:
            return await ctx.send("❌ **You must specify `specific_text` when using `contains` or `not_contains` filter.**", ephemeral=True)

        config = await self.get_channel_config(ctx.guild.id, ch.id)
        config["filter_mode"] = mode
        config["specific_text"] = specific_text
        config["enabled"] = True
        await self.save_channel_config(ctx.guild.id, ch.id, config)

        msg = f"Filter mode for {ch.mention} updated to `{mode}`"
        if specific_text:
            msg += f" (Query: `{specific_text}`)"
        await ctx.send(f"✧ **{msg}.**")

    @autodelete_group.command(name="roles", description="Manage role exemptions or target role filters.")
    @commands.has_permissions(manage_roles=True)
    async def autodelete_roles(
        self,
        ctx: commands.Context,
        action: Literal["exempt", "target", "remove_exempt", "remove_target", "clear"],
        role: Optional[discord.Role] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        await ctx.defer()
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        if action == "clear":
            config["exempt_roles"] = []
            config["target_roles"] = []
            await self.save_channel_config(ctx.guild.id, ch.id, config)
            return await ctx.send(f"✧ **Cleared all role rules for {ch.mention}.**")

        if not role:
            return await ctx.send("❌ **You must specify a role for this action.**", ephemeral=True)

        if action == "exempt":
            if role.id not in config["exempt_roles"]:
                config["exempt_roles"].append(role.id)
            msg = f"Role {role.mention} added to **exempt roles** (messages will not be deleted)."
        elif action == "target":
            if role.id not in config["target_roles"]:
                config["target_roles"].append(role.id)
            msg = f"Role {role.mention} added to **target roles** (ONLY messages from this role will be deleted)."
        elif action == "remove_exempt":
            if role.id in config["exempt_roles"]:
                config["exempt_roles"].remove(role.id)
            msg = f"Role {role.mention} removed from **exempt roles**."
        elif action == "remove_target":
            if role.id in config["target_roles"]:
                config["target_roles"].remove(role.id)
            msg = f"Role {role.mention} removed from **target roles**."

        await self.save_channel_config(ctx.guild.id, ch.id, config)
        await ctx.send(f"✧ **{msg}**")

    @autodelete_group.command(name="options", description="Toggle exemptions like pinned messages, bots, and admins.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_options(
        self,
        ctx: commands.Context,
        exempt_pinned: Optional[bool] = None,
        exempt_bots: Optional[bool] = None,
        exempt_admins: Optional[bool] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        await ctx.defer()
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        if exempt_pinned is not None:
            config["exempt_pinned"] = exempt_pinned
        if exempt_bots is not None:
            config["exempt_bots"] = exempt_bots
        if exempt_admins is not None:
            config["exempt_admins"] = exempt_admins

        await self.save_channel_config(ctx.guild.id, ch.id, config)
        await ctx.send(f"✧ **Updated auto-delete options for {ch.mention}:** Pinned Exempt: `{config['exempt_pinned']}`, Bots Exempt: `{config['exempt_bots']}`, Admins Exempt: `{config['exempt_admins']}`.")

    @autodelete_group.command(name="logchannel", description="Set an audit logging channel for auto-deleted messages.")
    @commands.has_permissions(manage_channels=True)
    async def autodelete_logchannel(self, ctx: commands.Context, log_channel: Optional[discord.TextChannel] = None, channel: Optional[discord.TextChannel] = None):
        await ctx.defer()
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        config["log_channel_id"] = log_channel.id if log_channel else None
        await self.save_channel_config(ctx.guild.id, ch.id, config)

        if log_channel:
            await ctx.send(f"✧ **Audit log channel for {ch.mention} set to {log_channel.mention}.**")
        else:
            await ctx.send(f"✧ **Disabled audit logging for {ch.mention}.**")

    @autodelete_group.command(name="disable", description="Deactivate auto-delete for a channel.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_disable(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await ctx.defer()
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        config["enabled"] = False
        await self.save_channel_config(ctx.guild.id, ch.id, config)
        await ctx.send(f"✧ **Auto-delete disabled for {ch.mention}.**")

    @autodelete_group.command(name="list", description="List all active auto-delete channels in this server.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_list(self, ctx: commands.Context):
        await ctx.defer()
        reg_key = f"autodelete:channels:{ctx.guild.id}"
        channel_ids = await rget_json(self.bot, reg_key) or []

        if not channel_ids:
            return await ctx.send("ℹ️ **No active auto-delete channels configured in this server.**", ephemeral=True)

        embed = discord.Embed(title="⚙️ 𝒜𝓊𝓉ℴ𝒟ℯ𝓁ℯ𝓉ℯ 𝒜𝒸𝓉𝒾𝓋ℯ 𝒞𝒽𝒶𝓃𝓃ℯ𝓁𝓈", color=0x9B59B6)
        active_count = 0

        for cid in channel_ids:
            ch = ctx.guild.get_channel(cid)
            if not ch:
                continue
            cfg = await self.get_channel_config(ctx.guild.id, cid)
            if cfg.get("enabled"):
                dur_text = format_seconds_to_duration(cfg.get("duration_seconds", 300))
                embed.add_field(
                    name=f"#{ch.name}",
                    value=f"• **Duration**: `{dur_text}`\n• **Filter**: `{cfg.get('filter_mode', 'all')}`",
                    inline=False
                )
                active_count += 1

        if active_count == 0:
            return await ctx.send("ℹ️ **No active auto-delete channels configured in this server.**", ephemeral=True)

        embed.set_footer(text=f"Total active channels: {active_count}")
        await self._send_embed(ctx, embed, fallback_text=f"Active AutoDelete Channels: {active_count} channels found.")

    @autodelete_group.command(name="process", description="Trigger an immediate scan and purge for a channel.")
    @commands.has_permissions(manage_messages=True)
    async def autodelete_process(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await ctx.defer(ephemeral=True)
        ch = channel or ctx.channel
        config = await self.get_channel_config(ctx.guild.id, ch.id)

        if not config.get("enabled"):
            return await ctx.send(f"❌ **Auto-delete is not enabled for {ch.mention}.**", ephemeral=True)

        purged_count = await self.run_channel_purge(ch, config)
        await ctx.send(f"✧ **Manual purge complete:** Removed **{purged_count}** expired messages from {ch.mention}.", ephemeral=True)

    async def run_channel_purge(self, channel: discord.TextChannel, config: dict) -> int:
        """Core purge execution for a single channel."""
        duration = config.get("duration_seconds", 300)
        if duration <= 0:
            return 0 # Instant mode handled by on_message

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=duration)
        to_delete = []

        try:
            async for message in channel.history(limit=200, before=cutoff):
                if self.should_delete_message(message, config):
                    to_delete.append(message)
                    if len(to_delete) >= 100:
                        break
        except Exception:
            return 0

        if not to_delete:
            return 0

        purged = 0
        try:
            # Split messages into bulk (<= 14 days old) and single deletes (> 14 days old)
            fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
            bulk_msgs = [m for m in to_delete if m.created_at > fourteen_days_ago]
            old_msgs = [m for m in to_delete if m.created_at <= fourteen_days_ago]

            if bulk_msgs:
                if len(bulk_msgs) == 1:
                    await bulk_msgs[0].delete()
                    purged += 1
                else:
                    deleted = await channel.purge(bulk=True, check=lambda m: m.id in [x.id for x in bulk_msgs])
                    purged += len(deleted)

            for m in old_msgs:
                try:
                    await m.delete()
                    purged += 1
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

        except discord.Forbidden:
            pass
        except Exception:
            pass

        if purged > 0 and config.get("log_channel_id"):
            log_ch = channel.guild.get_channel(config["log_channel_id"])
            if log_ch:
                embed = discord.Embed(
                    title="🧹 𝒜𝓊𝓉ℴ𝒟ℯ𝓁ℯ𝓉ℯ 𝒜𝓊𝒹𝒾𝓉 ℒℴ𝑔",
                    description=f"Purged **{purged}** expired messages in {channel.mention}.\n"
                                f"• **Interval**: `{format_seconds_to_duration(duration)}`\n"
                                f"• **Filter Mode**: `{config.get('filter_mode')}`",
                    color=0x95A5A6,
                    timestamp=datetime.now(timezone.utc)
                )
                await self._send_embed(log_ch, embed)

        return purged

    @tasks.loop(seconds=30)
    async def autodelete_loop(self):
        """Background worker scanning active auto-delete channels."""
        for guild in self.bot.guilds:
            try:
                reg_key = f"autodelete:channels:{guild.id}"
                channel_ids = await rget_json(self.bot, reg_key) or []
                for cid in channel_ids:
                    ch = guild.get_channel(cid)
                    if not ch or not isinstance(ch, discord.TextChannel):
                        continue
                    config = await self.get_channel_config(guild.id, cid)
                    if config.get("enabled") and config.get("duration_seconds", 300) > 0:
                        await self.run_channel_purge(ch, config)
                        await asyncio.sleep(1)
            except Exception:
                pass

    @autodelete_loop.before_loop
    async def before_autodelete_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Instant deletion enforcement for duration=0 mode."""
        if not message.guild or not isinstance(message.channel, discord.TextChannel):
            return

        config = await self.get_channel_config(message.guild.id, message.channel.id)
        if config.get("enabled") and config.get("duration_seconds") == 0:
            if self.should_delete_message(message, config):
                try:
                    await message.delete()
                    if config.get("log_channel_id"):
                        log_ch = message.guild.get_channel(config["log_channel_id"])
                        if log_ch:
                            embed = discord.Embed(
                                title="⚡ 𝒬𝓊𝒾𝒸𝓀 𝒜𝓊𝓉ℴ𝒟ℯ𝓁ℯ𝓉ℯ (ℐ𝓃𝓈𝓉𝒶𝓃𝓉)",
                                description=f"Deleted instant message by {message.author.mention} in {message.channel.mention}.\nContent: `{message.content[:200]}`",
                                color=0xE74C3C
                            )
                            await self._send_embed(log_ch, embed)
                except Exception:
                    pass

    @commands.hybrid_command(
        name="selfdestruct", 
        aliases=["sd", "timedmsg"], 
        description="Send a message that automatically self-destructs after a specified duration."
    )
    async def selfdestruct(
        self,
        ctx: commands.Context,
        duration: str,
        *,
        message: str
    ):
        sec = parse_duration_to_seconds(duration)
        if sec is None or sec <= 0:
            return await ctx.send("❌ **Invalid duration format.** Use e.g. `10s`, `30s`, `1m`, `5m`, `1h`.", ephemeral=True)

        if sec > 86400:
            return await ctx.send("❌ **Self-destruct duration cannot exceed 24 hours (24h).**", ephemeral=True)

        dur_text = format_seconds_to_duration(sec)
        
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        elif ctx.message:
            try:
                await ctx.message.delete()
            except:
                pass

        sent_msg = await ctx.channel.send(f"{message}\n\n*⏱️ This message will self-destruct in {dur_text}.*")

        if ctx.interaction:
            await ctx.send(f"✧ **Self-destruct message sent in {ctx.channel.mention}** (timer: `{dur_text}`).", ephemeral=True)

        await asyncio.sleep(sec)
        try:
            await sent_msg.delete()
        except:
            pass

async def setup(bot):
    if "AutoDeleteEngine" not in bot.cogs:
        await bot.add_cog(AutoDeleteEngine(bot))


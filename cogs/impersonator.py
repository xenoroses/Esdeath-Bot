import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from redis_utils import rget, rset, rdelete
import logging
from typing import Union, Optional

class Impersonator(commands.Cog):
    """
    Tier 3 Impersonation Engine.
    Hardened for multi-permission environments and premium aesthetics.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context, discord.Interaction], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized robust response handler for all engines."""
        if isinstance(dest, discord.Interaction):
            send_method = dest.followup.send if dest.response.is_done() else dest.response.send_message
        else:
            send_method = dest.send if hasattr(dest, "send") else dest
            
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            kwargs = {"embed": embed}
            if supports_ephemeral: kwargs["ephemeral"] = ephemeral
            await send_method(**kwargs)
        except discord.Forbidden:
            content = fallback_text or embed.description or "Action Processing..."
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹ℐ𝓉 (𝒫𝓁𝒶ℐ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                kwargs = {"content": fallback_msg}
                if supports_ephemeral: kwargs["ephemeral"] = ephemeral
                await send_method(**kwargs)
            except: pass
        except: pass

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Universal error handler for app commands in Impersonator cog."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            msg = str(error)
            if isinstance(error, app_commands.errors.MissingPermissions):
                msg = "You do not have permission to execute this command."
            await interaction.followup.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** {msg}", ephemeral=True)
        except Exception:
            pass

    @app_commands.command(name="say", description="Impersonate a user and send a message.")
    @app_commands.describe(user="The user to impersonate", message="The message to send")
    async def say(self, interaction: discord.Interaction, user: discord.Member, message: str):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        try:
            webhooks = await interaction.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Hyacine-Impersonator") or await interaction.channel.create_webhook(name="Hyacine-Impersonator")
            await webhook.send(content=message, username=user.display_name, avatar_url=user.display_avatar.url)
            embed = discord.Embed(description=f"✧ Message sent to {interaction.channel.mention}", color=0x5865F2)
            await self._send_embed(interaction, embed, ephemeral=True, fallback_text=f"Impersonated message sent to #{interaction.channel.name}")

            # Audit Logging for /say command
            if interaction.guild and (getattr(self.bot, 'redis', None) or hasattr(self.bot, 'cache')):
                try:
                    log_channel_id = await rget(self.bot, f"impersonator_log_channel:{interaction.guild.id}")
                    if log_channel_id:
                        log_channel = interaction.guild.get_channel(int(log_channel_id))
                        if log_channel:
                            log_embed = discord.Embed(
                                title="Impersonated message sent",
                                color=0x5865F2,
                                timestamp=datetime.now(timezone.utc)
                            )
                            log_embed.add_field(name="Sent as:", value=user.mention, inline=False)
                            log_embed.add_field(name="Message:", value=message[:1024], inline=False)
                            log_embed.add_field(name="Executed by", value=interaction.user.mention, inline=False)
                            log_embed.add_field(name="in channel", value=interaction.channel.mention, inline=False)
                            
                            now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
                            log_embed.set_footer(text=f"impersonator logs•{now_str}")
                            
                            await self._send_embed(log_channel, log_embed)
                except Exception as log_err:
                    logging.error(f"Failed to log impersonator action: {log_err}")

        except discord.Forbidden:
            await interaction.followup.send("⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Missing permissions to manage webhooks.", ephemeral=True)
        except discord.HTTPException as http_err:
            await interaction.followup.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Could not send message: {http_err.text or http_err}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** {e}", ephemeral=True)

    @commands.hybrid_command(name="saylog", description="Set or view the log channel for /say impersonation commands.")
    @commands.describe(channel="The text channel to send /say logs to. Omit to view current configuration.")
    @commands.has_permissions(administrator=True)
    async def saylog(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        await ctx.defer(ephemeral=True)
        key = f"impersonator_log_channel:{ctx.guild.id}"
        
        if channel is None:
            current = await rget(self.bot, key)
            if current:
                ch = ctx.guild.get_channel(int(current))
                ch_str = ch.mention if ch else f"<#{current}>"
                embed = discord.Embed(
                    title="🎭 ℐ𝓂𝓅ℯ𝓇𝓈ℴ𝓃𝒶𝓉ℴ𝓇 ℒℴ𝑔 𝒮ℯ𝓉𝓉𝒾𝓃𝑔𝓈",
                    description=f"Impersonator logs are currently set to {ch_str}.\n\nUse `/saylog channel:#channel` to change the channel, or `/saylogclear` to disable logging.",
                    color=0x5865F2
                )
            else:
                embed = discord.Embed(
                    title="🎭 ℐ𝓂𝓅ℯ𝓇𝓈ℴ𝓃𝒶𝓉ℴ𝓇 ℒℴ𝑔 𝒮ℯ𝓉𝓉𝒾𝓃𝑔𝓈",
                    description="No impersonator log channel configured.\n\nUse `/saylog channel:#channel` to designate an audit channel for `/say` commands.",
                    color=0x2B2D31
                )
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=embed.description)
            return

        try:
            await rset(self.bot, key, str(channel.id))
            embed = discord.Embed(
                title="✧ ℐ𝓂𝓅ℯ𝓇𝓈ℴ𝓃𝒶𝓉ℴ𝓇 ℒℴ𝑔 𝒞𝒽𝒶𝓃𝓃ℯ𝓁 𝒮ℯ𝓉",
                description=f"All `/say` command audit logs will now be transmitted to {channel.mention}.",
                color=0x5865F2
            )
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=f"Impersonator log channel set to #{channel.name}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to set log channel: {e}", ephemeral=True)

    @commands.hybrid_command(name="saylogclear", description="Clear and disable the log channel for /say command.")
    @commands.has_permissions(administrator=True)
    async def saylogclear(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        key = f"impersonator_log_channel:{ctx.guild.id}"
        try:
            await rdelete(self.bot, key)
            embed = discord.Embed(
                title="✧ ℐ𝓂𝓅ℯ𝓇𝓈ℴ𝓃𝒶𝓉ℴ𝓇 ℒℴ𝑔𝓈 𝒟𝒾𝓈𝒶𝒷𝓁ℯ𝒹",
                description="Impersonator audit logging has been cleared and disabled for this server.",
                color=0xE74C3C
            )
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text="Impersonator logging disabled.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Failed to clear log channel: {e}", ephemeral=True)

async def setup(bot):
    if "Impersonator" not in bot.cogs:
        await bot.add_cog(Impersonator(bot))


import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from redis_utils import rget
import logging
from typing import Union, Optional

class Impersonator(commands.Cog):
    """
    Tier 3 Impersonation Engine.
    Hardened for multi-permission environments and webhook resilience.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                kwargs = {"content": fallback_msg}
                if supports_ephemeral: kwargs["ephemeral"] = ephemeral
                await send_method(**kwargs)
            except: pass
        except: pass

    @app_commands.command(name="say", description="Impersonate a user and send a message.")
    @app_commands.describe(user="The user to impersonate", message="The message to send")
    @commands.has_permissions(administrator=True)
    async def say(self, interaction: discord.Interaction, user: discord.Member, message: str):
        await interaction.response.defer(ephemeral=True)
        try:
            webhooks = await interaction.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Hyacine-Impersonator") or await interaction.channel.create_webhook(name="Hyacine-Impersonator")
            
            await webhook.send(content=message, username=user.display_name, avatar_url=user.display_avatar.url)
            
            embed = discord.Embed(description=f"Message sent to {interaction.channel.mention}", color=0x5865F2)
            await self._send_embed(interaction, embed, ephemeral=True, fallback_text=f"Impersonated message sent to {interaction.channel.name}")
        except discord.Forbidden:
            await interaction.followup.send("Error: Missing permissions to manage webhooks.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"System error: {e}", ephemeral=True)

async def setup(bot):
    if "Impersonator" not in bot.cogs:
        await bot.add_cog(Impersonator(bot))

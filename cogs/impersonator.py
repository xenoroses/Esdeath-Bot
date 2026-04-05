import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from redis_utils import rget
import logging


class Impersonator(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="say",
        description="Impersonate a user and send a message."
    )
    @app_commands.describe(
        user="The user you want to impersonate",
        message="The message to send"
    )
    @commands.has_permissions(administrator=True)
    async def say(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        message: str
    ):

        # Immediate acknowledgement
        await interaction.response.send_message(
            f"Processing impersonation for {interaction.channel.mention}...",
            ephemeral=True
        )

        try:
            # Webhook handling
            webhooks = await interaction.channel.webhooks()

            webhook = discord.utils.get(
                webhooks,
                name="Hyacine-Impersonator"
            )

            if webhook is None:
                webhook = await interaction.channel.create_webhook(
                    name="Hyacine-Impersonator"
                )

            # Send impersonated message
            sent_message = await webhook.send(
                content=message,
                username=user.display_name,
                avatar_url=user.display_avatar.url,
                wait=True
            )

            # Logging (Guild-Specific Telemetry)
            log_cid = await rget(self.bot, f"log_channel:{interaction.guild.id}")
            log_channel = self.bot.get_channel(int(log_cid)) if log_cid else None

            if log_channel:

                log_embed = discord.Embed(
                    title="Impersonated message sent",
                    color=0x2B2D31,
                    timestamp=discord.utils.utcnow()
                )

                log_embed.add_field(
                    name="Sent as",
                    value=f"{user.mention} ({user.display_name})",
                    inline=False
                )

                log_embed.add_field(
                    name="Message",
                    value=message,
                    inline=False
                )

                log_embed.add_field(
                    name="Executed by",
                    value=interaction.user.mention,
                    inline=True
                )

                log_embed.add_field(
                    name="In channel",
                    value=interaction.channel.mention,
                    inline=True
                )

                log_embed.set_footer(
                    text="Impersonator Logs"
                )

                await log_channel.send(embed=log_embed)

            # Confirmation UI
            view = discord.ui.View()

            button = discord.ui.Button(
                label="View message",
                style=discord.ButtonStyle.link,
                url=sent_message.jump_url
            )

            view.add_item(button)

            confirm_embed = discord.Embed(
                description=f"Message sent to {interaction.channel.mention}",
                color=0x5865F2
            )

            await interaction.edit_original_response(
                content=None,
                embed=confirm_embed,
                view=view
            )

        except discord.Forbidden:

            await interaction.edit_original_response(
                content="Error: Missing Manage Webhooks permission in this channel."
            )

        except Exception as e:

            logging.error(f"Impersonator Error: {e}")

            await interaction.edit_original_response(
                content="System error occurred while sending impersonated message."
            )


async def setup(bot):
    if "Impersonator" not in bot.cogs:
        await bot.add_cog(Impersonator(bot))

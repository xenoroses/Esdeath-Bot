import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Impersonator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # IMPORTANT: Replace with your actual log channel ID
        self.LOG_CHANNEL_ID = 123456789012345678 

    @app_commands.command(name="say", description="Impersonate a user and send a message.")
    @app_commands.describe(user="The user you want to impersonate", message="The message to send")
    @commands.has_permissions(administrator=True)
    async def say(self, interaction: discord.Interaction, user: discord.Member, message: str):
        # 1. Immediate acknowledgement
        await interaction.response.send_message(f"Processing impersonation for {interaction.channel.mention}...", ephemeral=True)

        try:
            # 2. Webhook Handling
            # Fetch existing webhooks to find our specific one
            webhooks = await interaction.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Esdeath-Impersonator")
            
            # Create a webhook if it doesn't exist
            if not webhook:
                webhook = await interaction.channel.create_webhook(name="Esdeath-Impersonator")

            # 3. Send the impersonated message
            await webhook.send(
                content=message,
                username=user.display_name,
                avatar_url=user.display_avatar.url
            )

            # 4. Success Logging
            log_channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🎭 Impersonated message sent",
                    color=0x2b2d31,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Sent as", value=f"{user.mention} ({user.display_name})", inline=False)
                embed.add_field(name="Message", value=message, inline=False)
                embed.add_field(name="Executed by", value=interaction.user.mention, inline=True)
                embed.add_field(name="In channel", value=interaction.channel.mention, inline=True)
                embed.set_footer(text="Impersonator Logs")
                
                await log_channel.send(embed=embed)
            
            # Final silent confirmation
            await interaction.edit_original_response(content=f"✅ Message sent as **{user.display_name}**.")

        except discord.Forbidden:
            await interaction.edit_original_response(content="❌ **Error:** I don't have 'Manage Webhooks' permissions in this channel.")
        except Exception as e:
            print(f"Impersonator Error: {e}")
            await interaction.edit_original_response(content=f"❌ **System Error:** {e}")

async def setup(bot):
    await bot.add_cog(Impersonator(bot))
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class Impersonator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # IMPORTANT: Replace with your actual log channel ID
        self.LOG_CHANNEL_ID = 981221146110341176 

    @app_commands.command(name="say", description="Impersonate a user and send a message.")
    @app_commands.describe(user="The user you want to impersonate", message="The message to send")
    @commands.has_permissions(administrator=True)
    async def say(self, interaction: discord.Interaction, user: discord.Member, message: str):
        # 1. Immediate acknowledgement
        await interaction.response.send_message(f"Processing impersonation for {interaction.channel.mention}...", ephemeral=True)

        try:
            # 2. Webhook Handling
            webhooks = await interaction.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Esdeath-Impersonator")
            
            if not webhook:
                webhook = await interaction.channel.create_webhook(name="Esdeath-Impersonator")

            # 3. Send the impersonated message (wait=True gets the message URL back)
            sent_message = await webhook.send(
                content=message,
                username=user.display_name,
                avatar_url=user.display_avatar.url,
                wait=True 
            )

            # 4. Success Logging to your secret channel
            log_channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🎭 Impersonated message sent",
                    color=0x2b2d31,
                    timestamp=datetime.utcnow()
                )
                log_embed.add_field(name="Sent as", value=f"{user.mention} ({user.display_name})", inline=False)
                log_embed.add_field(name="Message", value=message, inline=False)
                log_embed.add_field(name="Executed by", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="In channel", value=interaction.channel.mention, inline=True)
                log_embed.set_footer(text="Impersonator Logs")
                
                await log_channel.send(embed=log_embed)
            
            # 5. Build the UI Button and Embed for the executor
            view = discord.ui.View()
            # Add the button linking to the message
            button = discord.ui.Button(label="View message", style=discord.ButtonStyle.link, url=sent_message.jump_url)
            view.add_item(button)
            
            # Create the dark blue confirmation embed
            confirm_embed = discord.Embed(
                description=f"Message sent to {interaction.channel.mention}", 
                color=0x5865F2 # Standard Discord blurple
            )

            # Final silent confirmation updating the "Processing..." text
            await interaction.edit_original_response(content=None, embed=confirm_embed, view=view)

        except discord.Forbidden:
            await interaction.edit_original_response(content="❌ **Error:** I don't have 'Manage Webhooks' permissions in this channel.")
        except Exception as e:
            print(f"Impersonator Error: {e}")
            await interaction.edit_original_response(content=f"❌ **System Error:** {e}")

async def setup(bot):
    await bot.add_cog(Impersonator(bot))
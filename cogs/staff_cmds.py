import discord
from discord.ext import commands
from discord import app_commands

class StaffCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="View server statistics.")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=f"Statistics for {g.name}", color=0x3498db)
        embed.add_field(name="Members", value=f"{g.member_count}", inline=True)
        embed.add_field(name="Created On", value=g.created_at.strftime("%b %d, %Y"), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="View member details.")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        embed = discord.Embed(title=f"Details for {user.display_name}", color=0xe74c3c)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%b %d, %Y"), inline=False)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%b %d, %Y") if user.joined_at else "N/A", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StaffCommands(bot))
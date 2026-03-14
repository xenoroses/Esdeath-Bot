import discord
from discord.ext import commands
from discord import app_commands
import time
from datetime import datetime, timedelta

class StaffCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    # --- SERVER INFO (From previous turn) ---
    @app_commands.command(name="serverinfo", description="Detailed statistics for this server.")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"Info for {g.name}", color=0x3498db)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=f"{g.owner.mention if g.owner else 'Unknown'}", inline=True)
        embed.add_field(name="Members", value=f"Total: {g.member_count}\nHumans: {humans}\nBots: {bots}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.set_footer(text=f"ID: {g.id} | Created: {g.created_at.strftime('%d/%m/%Y')}")
        await interaction.response.send_message(embed=embed)

    # --- USER INFO (From previous turn) ---
    @app_commands.command(name="userinfo", description="Detailed info about a member.")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        embed = discord.Embed(title=f"{user.display_name}", color=0xe74c3c)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y") if user.joined_at else "N/A", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        await interaction.response.send_message(embed=embed)

    # --- BATCH 1: NEW HIGH-LEVEL COMMANDS ---

    @app_commands.command(name="avatar", description="View a member's avatar.")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        embed = discord.Embed(title=f"Avatar for {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Check the bot's response time.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"It took me **{latency}ms** to notice you. Don't make me wait longer next time.")

    @app_commands.command(name="uptime", description="Check how long the bot has been online.")
    async def uptime(self, interaction: discord.Interaction):
        uptime_diff = datetime.utcnow() - self.start_time
        days = uptime_diff.days
        hours, remainder = divmod(uptime_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await interaction.response.send_message(f"I have been standing guard for **{days}d, {hours}h, {minutes}m, {seconds}s**.")

    @app_commands.command(name="echo", description="Make Esdeath say something.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def echo(self, interaction: discord.Interaction, message: str):
        # We send the message and then respond with a hidden "Done" message
        await interaction.channel.send(message)
        await interaction.response.send_message("Message delivered.", ephemeral=True)

    @app_commands.command(name="fancy", description="Convert text into 𝒻𝒶𝓃𝒸𝓎 𝓈𝒸𝓇𝒾𝓅𝓉.")
    async def fancy(self, interaction: discord.Interaction, text: str):
        # Dictionary for fancy cursive conversion
        mapping = str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
        )
        fancy_text = text.translate(mapping)
        await interaction.response.send_message(fancy_text)

async def setup(bot):
    await bot.add_cog(StaffCommands(bot))
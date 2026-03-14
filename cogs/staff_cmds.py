import discord
from discord.ext import commands
from discord import app_commands
import time
from datetime import datetime, timedelta

class StaffCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    # --- BATCH 1: IDENTITY & INFO ---

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
        await interaction.channel.send(message)
        await interaction.response.send_message("Message delivered.", ephemeral=True)

    @app_commands.command(name="fancy", description="Convert text into 𝒻𝒶𝓃𝒸𝓎 𝓈𝒸𝓇𝒾𝓅𝓉.")
    async def fancy(self, interaction: discord.Interaction, text: str):
        mapping = str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
        )
        fancy_text = text.translate(mapping)
        await interaction.response.send_message(fancy_text)

    # --- BATCH 2: MODERATION & DISCIPLINE ---

    @app_commands.command(name="kick", description="Remove a weakling from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You don't have the authority to remove someone stronger than you.", ephemeral=True)
        await member.kick(reason=reason)
        await interaction.response.send_message(f"**{member.display_name}** has been removed. I have no use for the weak.")

    @app_commands.command(name="ban", description="Permanently exile a user.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("I cannot exile someone of that rank.", ephemeral=True)
        await member.ban(reason=reason)
        await interaction.response.send_message(f"**{member.display_name}** has been exiled. Don't bother coming back.")

    @app_commands.command(name="timeout", description="Silence a user for a specific duration.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("I won't silence my superiors.", ephemeral=True)
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"**{member.display_name}** has been silenced for {minutes} minutes. Reflect on your failure.")

    @app_commands.command(name="purge", description="Delete a specific amount of messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount > 100:
            return await interaction.response.send_message("I'm not cleaning up more than 100 messages at once. Do it yourself.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"I've vaporized {len(deleted)} messages. The chat is clean now.")

    @app_commands.command(name="slowmode", description="Set the channel's slowmode delay.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("Slowmode has been disabled. Talk as much as you want.")
        else:
            await interaction.response.send_message(f"Slowmode set to {seconds} seconds. Think before you speak.")

# --- THIS FUNCTION MUST BE AT THE VERY BOTTOM OUTSIDE THE CLASS ---
async def setup(bot):
    await bot.add_cog(StaffCommands(bot))
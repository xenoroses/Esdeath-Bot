import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import requests
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

    # --- BATCH 3: INTERACTIVE TOOLS ---

    @app_commands.command(name="poll", description="Create a professional poll.")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        option_list = [opt.strip() for opt in options.split(",")]
        if len(option_list) > 10:
            return await interaction.response.send_message("I'm not counting more than 10 options. Keep it simple.", ephemeral=True)
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        description = ""
        for i, option in enumerate(option_list):
            description += f"{emojis[i]} {option}\n\n"
            
        embed = discord.Embed(title=f"📊 {question}", description=description, color=0x3498db)
        embed.set_footer(text=f"Poll started by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
        poll_msg = await interaction.original_response()
        for i in range(len(option_list)):
            await poll_msg.add_reaction(emojis[i])

    @app_commands.command(name="embed", description="Make Esdeath post a custom colored box.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def embed(self, interaction: discord.Interaction, title: str, description: str, color: str = "blue"):
        color_map = {"blue": 0x3498db, "red": 0xe74c3c, "green": 0x2ecc71, "gold": 0xf1c40f}
        hex_color = color_map.get(color.lower(), 0x3498db)
        
        custom_embed = discord.Embed(title=title, description=description, color=hex_color)
        custom_embed.set_footer(text=f"Official Notice from {interaction.guild.name}")
        
        await interaction.channel.send(embed=custom_embed)
        await interaction.response.send_message("Embed deployed.", ephemeral=True)

    @app_commands.command(name="remind", description="Set a personal reminder.")
    async def remind(self, interaction: discord.Interaction, minutes: int, note: str):
        await interaction.response.send_message(f"Fine. I'll remind you about '{note}' in {minutes} minutes.", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try:
            await interaction.user.send(f"Hey. You told me to remind you: **{note}**")
        except:
            await interaction.channel.send(f"{interaction.user.mention}, listen up. You wanted to be reminded: **{note}**")

    # --- BATCH 4: ADVANCED UTILITY & FUN ---

    @app_commands.command(name="urban", description="Look up a term on Urban Dictionary.")
    async def urban(self, interaction: discord.Interaction, term: str):
        url = f"https://api.urbandictionary.com/v0/define?term={term}"
        response = requests.get(url).json()
        
        if not response['list']:
            return await interaction.response.send_message(f"Even the internet doesn't know what '{term}' means. How pathetic.", ephemeral=True)
        
        first_entry = response['list'][0]
        definition = first_entry['definition'].replace("[", "").replace("]", "")
        example = first_entry['example'].replace("[", "").replace("]", "")
        
        embed = discord.Embed(title=f"Definition: {term}", color=0x1D2439)
        embed.add_field(name="What it is:", value=definition[:1024], inline=False)
        if example:
            embed.add_field(name="Example:", value=f"*{example[:1024]}*", inline=False)
        
        embed.set_footer(text=f"👍 {first_entry['thumbs_up']} | 👎 {first_entry['thumbs_down']}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="math", description="Solve a basic math problem.")
    async def math(self, interaction: discord.Interaction, expression: str):
        # Using a safe way to evaluate simple math
        try:
            # Remove any dangerous characters
            allowed = "0123456789+-*/(). "
            if all(c in allowed for c in expression):
                result = eval(expression)
                await interaction.response.send_message(f"The answer is **{result}**. Honestly, you couldn't solve that yourself?")
            else:
                await interaction.response.send_message("Don't try to hack me with your weird symbols.", ephemeral=True)
        except:
            await interaction.response.send_message("That's not even a valid equation.", ephemeral=True)

    @app_commands.command(name="roll", description="Roll some dice (e.g., 2d6).")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        try:
            amount, sides = map(int, dice.lower().split('d'))
            if amount > 100 or sides > 1000:
                return await interaction.response.send_message("I'm not rolling that many dice. Stop being extra.", ephemeral=True)
            
            rolls = [random.randint(1, sides) for _ in range(amount)]
            total = sum(rolls)
            await interaction.response.send_message(f"🎲 Rolling **{dice}**... You got: `{rolls}` (Total: **{total}**)")
        except:
            await interaction.response.send_message("Format it correctly, like `2d20`.", ephemeral=True)

    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"🪙 The coin landed on... **{result}**.")

    @app_commands.command(name="membercount", description="See the breakdown of members.")
    async def membercount(self, interaction: discord.Interaction):
        g = interaction.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        
        embed = discord.Embed(title=f"Member Count for {g.name}", color=0x2ecc71)
        embed.add_field(name="Total Members", value=f"**{g.member_count}**", inline=False)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        
        await interaction.response.send_message(embed=embed)


# --- GLOBAL SETUP FUNCTION ---
async def setup(bot):
    await bot.add_cog(StaffCommands(bot))
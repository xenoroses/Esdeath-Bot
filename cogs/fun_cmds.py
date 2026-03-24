import discord
from discord.ext import commands
import random

class FunCmds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="match", description="Calculate the love score between two users!")
    async def match(self, ctx: commands.Context, user1: discord.Member, user2: discord.Member = None):
        
        # If they only ping one user, match the sender with the pinged user
        if user2 is None:
            user2 = user1
            user1 = ctx.author

        # Seed the random number generator so the same pair always gets the same results
        ids = sorted([user1.id, user2.id])
        random.seed(f"{ids[0]}{ids[1]}")
        
        # 1. Roll the Love Score
        score = random.randint(0, 100)
        
        # 2. Roll the Luck-Based "Shipped?" Status
        shipped_roll = random.randint(1, 100)
        shipped = "Yes! 💍" if shipped_roll > 85 else "No :("
            
        random.seed() # Reset the seed immediately

        # Dynamic aesthetic changes based on the score
        if score >= 90:
            conclusion = "A literal match made in heaven. ✨"
            embed_color = discord.Color.from_rgb(255, 20, 147) # Deep Pink
        elif score >= 75:
            conclusion = "There are definitely some sparks flying. ❤️‍🔥"
            embed_color = discord.Color.from_rgb(255, 105, 180) # Hot Pink
        elif score >= 50:
            conclusion = "There is potential, but it needs work. 🌱"
            embed_color = discord.Color.from_rgb(255, 182, 193) # Light Pink
        elif score >= 25:
            conclusion = "Friendzone territory. 🧊"
            embed_color = discord.Color.light_grey()
        else:
            conclusion = "Do not even try it. 💀"
            embed_color = discord.Color.dark_grey()

        # Build the Visual Love Meter (10 blocks total)
        filled_blocks = int(score / 10)
        empty_blocks = 10 - filled_blocks
        # Uses Discord's built-in block characters for a clean progress bar
        love_meter = ("█" * filled_blocks) + ("░" * empty_blocks)

        # Build the aesthetic Embed
        embed = discord.Embed(
            description=f"Testing compatibility between **{user1.display_name}** and **{user2.display_name}**...\n\n"
                        f"**Love Meter:**\n"
                        f"`[{love_meter}]` **{score}%**\n\n"
                        f"**Conclusion:** {conclusion}\n"
                        f"**Shipped?** {shipped}",
            color=embed_color
        )
        
        # Adds a clean header with your bot's avatar
        embed.set_author(name="Esdeath Matchmaking System", icon_url=self.bot.user.display_avatar.url)
        
        # Adds the target's profile picture to the top right corner
        embed.set_thumbnail(url=user2.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FunCmds(bot))
import discord
from discord.ext import commands
import random


class FunCmds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(
        name="match",
        description="Calculate the love score between two users!",
        aliases=["ship", "love"]
    )
    async def match(
        self,
        ctx: commands.Context,
        user1: discord.Member,
        user2: discord.Member = None
    ):
        """Calculates compatibility between users."""

        # If only one user is provided, match author with that user
        if user2 is None:
            user2 = user1
            user1 = ctx.author

        # Deterministic pairing result
        ids = sorted([user1.id, user2.id])
        random.seed(f"{ids[0]}{ids[1]}")

        score = random.randint(0, 100)

        shipped_roll = random.randint(1, 100)
        shipped = "Yes! 💍" if shipped_roll > 85 else "No :("

        # Reset RNG immediately
        random.seed()

        # Dynamic embed styling
        if score >= 90:
            conclusion = "A literal match made in heaven. ✨"
            embed_color = discord.Color.from_rgb(255, 20, 147)

        elif score >= 75:
            conclusion = "There are definitely some sparks flying. ❤️‍🔥"
            embed_color = discord.Color.from_rgb(255, 105, 180)

        elif score >= 50:
            conclusion = "There is potential, but it needs work. 🌱"
            embed_color = discord.Color.from_rgb(255, 182, 193)

        elif score >= 25:
            conclusion = "Friendzone territory. 🧊"
            embed_color = discord.Color.light_grey()

        else:
            conclusion = "Do not even try it. 💀"
            embed_color = discord.Color.dark_grey()

        # Visual love meter
        filled_blocks = int(score / 10)
        empty_blocks = 10 - filled_blocks
        love_meter = ("█" * filled_blocks) + ("░" * empty_blocks)

        embed = discord.Embed(
            description=(
                f"Testing compatibility between **{user1.display_name}** "
                f"and **{user2.display_name}**...\n\n"
                f"**Love Meter:**\n"
                f"`[{love_meter}]` **{score}%**\n\n"
                f"**Conclusion:** {conclusion}\n"
                f"**Shipped?** {shipped}"
            ),
            color=embed_color
        )

        # Safe avatar fallback protection
        bot_avatar = (
            self.bot.user.display_avatar.url
            if self.bot.user
            else None
        )

        if bot_avatar:
            embed.set_author(
                name="Esdeath Matchmaking System",
                icon_url=bot_avatar
            )

        embed.set_thumbnail(
            url=user2.display_avatar.url
        )

        await ctx.send(embed=embed)


async def setup(bot):
    if "FunCmds" not in bot.cogs:
        await bot.add_cog(FunCmds(bot))
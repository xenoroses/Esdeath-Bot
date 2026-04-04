import discord
from discord.ext import commands
import random


class FunCmds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(
        name="match",
        description="Calculate the resonance between two users.",
        aliases=["ship", "love"]
    )
    async def match(
        self,
        ctx: commands.Context,
        user1: discord.Member,
        user2: discord.Member = None
    ):
        """Calculates compatibility between users with high-density analysis."""
        await ctx.defer()
        
        # If only one user is provided, match author with that user
        if user2 is None:
            user2 = user1
            user1 = ctx.author

        # Deterministic pairing result (Billion-Dollar Precision)
        ids = sorted([user1.id, user2.id])
        seed_val = f"{ids[0]}{ids[1]}"
        rng = random.Random(seed_val)

        score = rng.randint(0, 100)
        
        # Detailed Sub-metrics (Albert Einstein Level)
        physical = rng.randint(40, 100) if score > 50 else rng.randint(10, 60)
        emotional = rng.randint(40, 100) if score > 60 else rng.randint(10, 70)
        destiny = rng.randint(5, 99)

        # Hyacine Cutesy Aesthetic
        embed = discord.Embed(
            title=f"✧ 𝒮𝓎𝓃𝒶𝓅𝓉𝒾𝒸 ℳ𝒶𝓉𝒸𝒽𝓂𝒶𝓀𝒾𝓃𝑔",
            color=0xB19CD9 # Hyacine Lavender
        )
        embed.set_author(name=f"{user1.display_name} ⟡ {user2.display_name}", icon_url=user1.display_avatar.url)
        embed.set_thumbnail(url=user2.display_avatar.url)

        # Dynamic Conclusion Logic (No Emojis)
        if score >= 90:
            conclusion = "A perfect cosmic alignment. Resonance is absolute. ✧"
        elif score >= 70:
            conclusion = "High vibrational synergy detected. Flow is stable. ❂"
        elif score >= 40:
            conclusion = "Moderate resonance. Potential for synchronization exists. ⌬"
        else:
            conclusion = "Low frequency match. Interference is likely. ⟡"

        # Cutesy Progress Bar
        prog_bar = "✧" * int(score / 10) + "◈" * (10 - int(score / 10))

        details = (
            f"**» Resonance Sync**\n"
            f"Overall Harmony: **{score}%**\n"
            f"Pulse Status: `[{prog_bar}]` \n\n"
            f"**» Compatibility Matrix**\n"
            f"Physical: **{physical}%** ⟡ Emotional: **{emotional}%**\n"
            f"Destiny Factor: **{destiny}%**\n\n"
            f"**» Final Oracle**\n"
            f"*{conclusion}*"
        )
        embed.description = details
        embed.set_footer(text="© Hyacine Matchmaking | Orbital Synergy Data", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)


async def setup(bot):
    if "FunCmds" not in bot.cogs:
        await bot.add_cog(FunCmds(bot))

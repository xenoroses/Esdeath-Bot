import discord
from discord.ext import commands
import random
import asyncio
import httpx

class FunCmds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, ctx, embed, ephemeral=False, fallback_text=None):
        """Internal robust sender that handles missing 'Embed Links' permission gracefully."""
        try:
            await ctx.send(embed=embed, ephemeral=ephemeral)
        except discord.Forbidden as e:
            if e.code == 50013: # Missing Permissions
                content = fallback_text or embed.description or "Action Successful."
                header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
                await ctx.send(f"{header}```fix\n{content}\n``` {footer}", ephemeral=ephemeral)
            else:
                raise e


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

        await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓎𝓃𝒶Ⓟ𝓉𝒾𝒸 ℳ𝒶𝓉ℿ𝒽: {user1.display_name} + {user2.display_name} = **{score}%** Harmony.")

    @commands.hybrid_command(name="urban", description="Search the Urban Dictionary (Stellar slang audit).")
    async def urban(self, ctx: commands.Context, *, term: str):
        await ctx.defer()
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"https://api.urbandictionary.com/v0/define?term={term}")
                data = resp.json()
            except:
                return await ctx.send("⌬ ⟡ **𝒩ℯ𝓉𝓌ℴ𝓇𝓀 ℐ𝓃𝓉ℯ𝓇𝒻ℯ𝓇ℯ𝓃𝒸ℯ.** Urban Dictionary is unreachable.")
        
        if not data['list']:
            return await ctx.send("⌬ ⟡ **𝒩ℴ 𝒹ℯ𝒻𝒾𝓃𝒾𝓉𝒾ℴ𝓃 𝒻ℴ𝓊𝓃𝒹 𝒾𝓃 𝓉𝒽ℯ 𝓋ℴ𝒾𝒹.**")
        
        top = data['list'][0]
        embed = discord.Embed(title=f"✧ 𝒰𝓇𝒷𝒶𝓃 𝒜𝓊𝒹𝒾𝓉: {term}", description=top['definition'].replace("[", "").replace("]", ""), color=0x9B59B6)
        embed.add_field(name="Example", value=top['example'].replace("[", "").replace("]", "") or "No example.")
        await self._send_embed(ctx, embed, fallback_text=f"𝒰𝓇𝒷𝒶𝓃 𝒜𝓊𝒹𝒾𝓉 ({term}): {top['definition'][:200]}...")

    @commands.hybrid_command(name="poll", description="Create a simple demographic sync (poll).")
    async def poll(self, ctx: commands.Context, question: str, opt1: str, opt2: str):
        embed = discord.Embed(title="❂ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒟ℯ𝓂ℴℊ𝓇𝒶𝓅ℋ𝒾𝒸 𝒮𝓎𝓃𝒸", description=f"**{question}**\n\n1️⃣ {opt1}\n2️⃣ {opt2}", color=0xB19CD9)
        try:
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("1️⃣")
            await msg.add_reaction("2️⃣")
        except discord.Forbidden as e:
            if e.code == 50013:
                await ctx.send(f"❂ **𝒫ℴ𝓁𝓁:** {question}\n1. {opt1}\n2. {opt2}\n(Reactions/Embeds disabled)")
            else:
                raise e

    @commands.hybrid_command(name="remind", description="Set a temporal resonance alert.")
    async def remind(self, ctx: commands.Context, minutes: int, *, task: str):
        await ctx.send(f"✧ Temporal anchor set for **{minutes}m**. I will pulse you then.", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try:
            await ctx.author.send(f"❂ ⟡ **𝒯ℯ𝓂ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ:** {task}")
        except:
            await ctx.send(f"{ctx.author.mention} ❂ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃ℯ:** {task}")


async def setup(bot):
    if "FunCmds" not in bot.cogs:
        await bot.add_cog(FunCmds(bot))

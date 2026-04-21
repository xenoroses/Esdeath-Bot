import discord
from discord.ext import commands
import random
import asyncio
import httpx
from typing import Union, Optional

class FunCmds(commands.Cog):
    """
    Tier 1 Fun Commands.
    Hardened for multi-permission environments and premium aesthetics.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized robust response handler for all engines."""
        send_method = dest.send if hasattr(dest, "send") else dest
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            if supports_ephemeral:
                await send_method(embed=embed, ephemeral=ephemeral)
            else:
                await send_method(embed=embed)
        except discord.Forbidden:
            content = fallback_text or embed.description or "Action Processing..."
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹ℐ𝓉 (𝒫𝓁𝒶ℐ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                if supports_ephemeral:
                    await send_method(fallback_msg, ephemeral=ephemeral)
                else:
                    await send_method(fallback_msg)
            except:
                pass
        except:
            pass

    @commands.hybrid_command(name="match", description="Calculate resonance between two users.")
    async def match(self, ctx: commands.Context, user1: discord.Member, user2: discord.Member = None):
        await ctx.defer()
        user2 = user2 or ctx.author
        score = random.randint(0, 100)
        embed = discord.Embed(title="✧ 𝒮𝓎𝓃𝒶𝓅Ⓟ𝓉𝒾𝒸 ℳ𝒶𝓉𝒸𝒽𝓂𝒶𝓀𝒾𝓃𝑔", color=0xB19CD9)
        embed.description = f"Overall Harmony: **{score}%**\nResonance level: Stable."
        await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓎𝓃𝒶𝓅Ⓟ𝓉𝒾𝒸 ℳ𝒶т𝒸𝒽: {user1.display_name} + {user2.display_name} = **{score}%**.")

    @commands.hybrid_command(name="urban", description="Search Urban Dictionary.")
    async def urban(self, ctx: commands.Context, *, term: str):
        await ctx.defer()
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"https://api.urbandictionary.com/v0/define?term={term}")
                data = resp.json()
                if not data['list']: return await ctx.send("⌬ ⟡ **𝒩ℴ 𝒹ℯ𝒻𝒾𝓃𝒾𝓉𝒾ℴ𝓃 𝒻ℴ𝓊𝓃𝒹.**")
                top = data['list'][0]
                embed = discord.Embed(title=f"✧ 𝒰𝓇𝒷𝒶𝓃 𝒜𝓊𝒹𝒾𝓉: {term}", description=top['definition'].replace("[", "").replace("]", ""), color=0x9B59B6)
                await self._send_embed(ctx, embed, fallback_text=f"𝒰𝓇𝒷𝒶𝓃 𝒜𝓭𝓲𝓽: {top['definition'][:200]}...")
            except:
                await ctx.send("⌬ ⟡ **𝒩ℯ𝓉𝓌ℴ𝓇𝓀 𝒾𝓃𝓉ℯ𝓇𝒻ℯ𝓇ℯ𝓃𝒸ℯ.**")

    @commands.hybrid_command(name="poll", description="Create s simple poll.")
    async def poll(self, ctx: commands.Context, question: str, opt1: str, opt2: str):
        embed = discord.Embed(title="❂ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒮𝓎𝓃𝒸", description=f"**{question}**\n\n1. {opt1}\n2. {opt2}", color=0xB19CD9)
        await self._send_embed(ctx, embed, fallback_text=f"❂ **𝒫ℴ𝓁𝓁:** {question}\n1. {opt1}\n2. {opt2}")

    @commands.hybrid_command(name="remind", description="Set a temporal resonance alert.")
    async def remind(self, ctx: commands.Context, minutes: int, *, task: str):
        await ctx.send(f"✧ Temporal anchor set for **{minutes}m**.", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try: await ctx.author.send(f"❂ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ:** {task}")
        except: await ctx.send(f"{ctx.author.mention} ❂ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ:** {task}")

async def setup(bot):
    if "FunCmds" not in bot.cogs:
        await bot.add_cog(FunCmds(bot))

import discord
from discord.ext import commands
import random
import json
from redis_utils import rget, rset, rget_json, rset_json
from typing import Union, Optional

class SocialEngine(commands.Cog):
    """
    Tier 2 Social Dynamics: Judgement, Fealty, and Vendettas.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾Audit (𝒫𝓁𝒶ℒ𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
            fallback_msg = f"{header}```fix\n{content}\n``` {footer}"
            try:
                if supports_ephemeral:
                    await send_method(fallback_msg, ephemeral=ephemeral)
                else:
                    await send_method(fallback_msg)
            except:
                pass
        exceptException:
            pass

    @commands.hybrid_command(name="judgement", description="AI profiling of a member.")
    async def judgement(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
             verdicts = ["STELLAR PARASITE ⌬", "AEON GUARDIAN ✧", "VOID DRIFTER ⌬"]
             verdict = random.choice(verdicts)
             embed = discord.Embed(title=f"⚖️ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒥𝓊𝒹𝑔ℯ𝓂ℯ𝓃𝓉: {user.display_name}", color=0x2c3e50)
             embed.description = f"VERDICT: **{verdict}**"
             await self._send_embed(ctx, embed, fallback_text=f"𝒥𝓊𝒹𝑔ℯ𝓂ℯ𝓃𝓉 of {user.display_name}: {verdict}")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Judgement core failed: {e}")

    @commands.hybrid_command(name="fealty", description="Measure allegiance.")
    async def fealty(self, ctx: commands.Context, user: discord.Member):
        score = random.randint(0, 100)
        embed = discord.Embed(title=f"🏹 ℱℯ𝒶𝓁𝓉𝓎 𝒮𝒸𝒶𝓃: {user.display_name}", color=0x27ae60)
        embed.description = f"Allegiance Score: **{score}%**"
        await self._send_embed(ctx, embed, fallback_text=f"ℱℯ𝒶𝓁𝓉𝓎 of {user.display_name}: {score}%")

async def setup(bot):
    if "SocialEngine" not in bot.cogs:
        await bot.add_cog(SocialEngine(bot))

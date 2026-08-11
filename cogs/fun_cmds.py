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

    @commands.hybrid_command(name="remind", description="Set a temporal resonance alert.")
    async def remind(self, ctx: commands.Context, minutes: int, *, task: str):
        await ctx.send(f"✧ Temporal anchor set for **{minutes}m**.", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try: await ctx.author.send(f"❂ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ:** {task}")
        except: await ctx.send(f"{ctx.author.mention} ❂ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ:** {task}")

async def setup(bot):
    if "FunCmds" not in bot.cogs:
        await bot.add_cog(FunCmds(bot))

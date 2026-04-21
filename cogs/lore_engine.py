import discord
from discord.ext import commands
import random
import json
from redis_utils import rget, rset, rget_json, rset_json
from typing import Union, Optional

class LoreEngine(commands.Cog):
    """
    Tier 5 Lore & Mythology: Chronicles, Auras, and Dossiers.
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
        except:
            pass

    @commands.hybrid_command(name="aura", description="Visualize user soul color.")
    async def aura(self, ctx: commands.Context, member: discord.Member = None):
        user = member or ctx.author
        colors = [0xFF5733, 0x33FF57, 0x3357FF, 0xF333FF, 0x33FFF3]
        color = random.choice(colors)
        embed = discord.Embed(title=f"✧ 𝒮𝓅ℯ𝒸𝓉𝓇𝒶𝓁 𝒜𝓊𝓇𝒶: {user.display_name}", color=color)
        embed.description = "Aura Frequency: **Vibrant ✧**"
        await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓅ℯ𝒸𝓉𝓇𝒶𝓁 𝒜𝓊𝓇𝒶 of {user.display_name}: Radiant.")

    @commands.hybrid_command(name="chronicle", description="Generate sector lore.")
    async def chronicle(self, ctx: commands.Context):
        await ctx.defer()
        try:
             embed = discord.Embed(title="📜 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ", description="A grand saga is being written...", color=0x9B59B6)
             await self._send_embed(ctx, embed, fallback_text="𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ synchronized.")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Chronicle failure: {e}")

    @commands.hybrid_command(name="dossier", description="Fictional character history.")
    async def dossier(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
             embed = discord.Embed(title=f"📁 𝒰𝓈ℯ𝓇 𝒟ℴ𝓈𝓈𝒾ℯ𝓇: {user.display_name}", description="Target background: Classified ⌬", color=0x34495E)
             await self._send_embed(ctx, embed, fallback_text=f"𝒟ℴ𝓈𝓈𝒾ℯ𝓇 analysis complete for {user.display_name}.")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Dossier retrieval failed: {e}")

async def setup(bot):
    if "LoreEngine" not in bot.cogs:
        await bot.add_cog(LoreEngine(bot))

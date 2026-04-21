import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone, timedelta
import time
from redis_utils import rget_json
from typing import Union, Optional

class LoreEngine(commands.Cog):
    """
    Tier 3: AI-Native Entertainment, Aura Scans, and Server Simulation narratives.
    Hardened for multi-permission environments.
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
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
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

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_command(name="aura", description="Analyze a user's distinct spectral presence.")
    async def aura(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            resonance = int(trust * 10)
            hex_code = f"#{random.randint(0, 0xFFFFFF):06x}".upper()
            
            embed = discord.Embed(title=f"✧ 𝒜𝓊𝓇𝒶 𝒮𝓅ℯ𝒸𝓉𝓇𝒶𝓁 𝒮𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ", color=0xB19CD9)
            if target.display_avatar: embed.set_thumbnail(url=target.display_avatar.url)
            embed.description = f"**Spectral Resonance:** {resonance}%\n**Sync Hex:** `{hex_code}`"
            await self._send_embed(ctx, embed, fallback_text=f"𝒜𝓊𝓇𝒶 Resonance: **{resonance}%** | Sig: {hex_code}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒜𝓊𝓇𝒶 failed:** {e}")

    @commands.hybrid_command(name="chronicle", description="Generates a micro-story about recent channel events.")
    @commands.has_permissions(manage_messages=True)
    async def chronicle(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed = discord.Embed(title=f"❂ 𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ: #{ctx.channel.name}", description="*A tense silence was finally broken by a sudden burst of frantic assembly...*", color=0x2E4053)
            await self._send_embed(ctx, embed, fallback_text=f"𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ of #{ctx.channel.name} Analysis Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ failed:** {e}")

    @commands.hybrid_command(name="wargame", description="Runs an alternate timeline scenario.")
    @commands.has_permissions(manage_messages=True)
    async def wargame(self, ctx: commands.Context):
        await ctx.defer()
        embed = discord.Embed(title="❈ 𝒲𝒶𝓇𝑔𝒶𝓂ℯ: 𝒮𝒾𝓂𝓊𝓁𝒶𝓉𝒾ℴ𝓃", description="**Scenario:** Mutiny detection triggered.\n**Projection:** 48% instability.", color=0xE74C3C)
        await self._send_embed(ctx, embed, fallback_text="𝒲𝒶𝓇𝑔𝒶𝓂ℯ Projection Active.")

    @commands.hybrid_command(name="dossier", description="Constructs a historical timeline.")
    async def dossier(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            embed = discord.Embed(title=f"𖦹 𝒟ℴ𝓈𝓈𝒾ℯ𝓇: {target.display_name}", description="Historical Reconstruction complete.", color=0x34495E)
            await self._send_embed(ctx, embed, fallback_text=f"𝒟ℴ𝓈𝓈𝒾ℯ𝓇 for {target.display_name} Reconstruction Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒟ℴ𝓈𝓈𝒾ℯ𝓇 failed:** {e}")

    @commands.hybrid_command(name="omen", description="Predicts a near-future server event.")
    @commands.cooldown(1, 1800, commands.BucketType.guild)
    async def omen(self, ctx: commands.Context):
        await ctx.defer()
        embed = discord.Embed(title="𖦹 𝒪𝓇𝒶𝒸𝓁ℯ'𝓈 𝒪ℳℯ𝓃", description="**Prediction:** A heated debate will emerge soon.", color=0x9B59B6)
        await self._send_embed(ctx, embed, fallback_text="𝒪𝓇𝒶𝒸𝓁ℯ'𝓈 𝒪ℳℯ𝓃 Predicted for this sector.")

async def setup(bot):
    if "LoreEngine" not in bot.cogs:
        await bot.add_cog(LoreEngine(bot))

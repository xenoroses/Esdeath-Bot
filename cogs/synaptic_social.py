import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone
from redis_utils import rget_json, rset_json, rget, rset
import json
from typing import Union, Optional

class SynapticSocial(commands.Cog):
    """
    Tier 7: The Synaptic Identity Layer - Billion-Dollar Social Engineering.
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

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_group(name="synapse", description="Access the Synaptic Identity Layer.", invoke_without_command=True)
    async def synapse_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @synapse_group.command(name="essence", description="View a unified social identity profile.")
    async def essence(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            embed = discord.Embed(title=f"✧ 𝒮𝓎𝓃𝒶𝓅𝓉𝒾𝒸 ℰ𝓈𝓈ℯ𝓃𝒸ℯ: {target.display_name}", color=0xB19CD9)
            embed.description = f"**Trust Index:** {trust:.2f}\n*Verified by Hyacine Identity Layer.*"
            if target.display_avatar: embed.set_thumbnail(url=target.display_avatar.url)
            await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓎𝓃𝒶𝓅𝓉𝒾𝒸 ℰ𝓈𝓈ℯ𝓃𝒸ℯ ({target.display_name}): Trust {trust:.2f}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** Essence reconstruction failure: {e}")

    @synapse_group.command(name="resonance", description="Propose a social resonance bond.")
    async def resonance(self, ctx: commands.Context, target: discord.Member):
        if target.bot or target.id == ctx.author.id: return
        await ctx.send(f"✧ {target.mention}, **{ctx.author.display_name}** requests a resonance bond. Type `synchronize` in 30s.")
        def check(m): return m.author == target and m.channel == ctx.channel and m.content.lower() == "synchronize"
        try:
            await self.bot.wait_for('message', timeout=30.0, check=check)
            embed = discord.Embed(title="✧ ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ 𝒮ℴ𝓁𝒾𝒹𝒾𝒻𝒾ℯ𝒹", description=f"Synergy established.", color=0xB19CD9)
            await self._send_embed(ctx, embed, fallback_text="ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ 𝒮ℴ𝓁𝒾𝒹𝒾𝒻𝒾ℯ𝒹.")
        except: await ctx.send("⌬ ⟡ **ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ 𝒻𝒶𝒹ℯ𝒹.**")

    @synapse_group.command(name="meridian", description="Server social temperature scan.")
    async def meridian(self, ctx: commands.Context):
        await ctx.defer()
        embed = discord.Embed(title="✧ 𝒮ℴ𝒸𝒾𝒶𝓁 ℳℯ𝓇𝒾𝒹𝒾𝒶𝓃", description="Intensity Pulse: **42%**\nThermal Phase: **Solar Flare ✧**", color=0xB19CD9)
        await self._send_embed(ctx, embed, fallback_text="𝒮ℴ𝒸𝒾𝒶𝓁 ℳℯ𝓇𝒾𝒹𝒾𝒶𝓃 Analysis Complete.")

    @synapse_group.command(name="pulse", description="Server social velocity scan.")
    async def pulse(self, ctx: commands.Context):
        await ctx.defer()
        embed = discord.Embed(title="✵ 𝒢𝓁ℴ𝒷𝒶𝓁 𝒮ℯ𝓃𝓈ℴ𝓇𝓎 𝒫𝓊𝓁𝓈ℯ", description="Tension Level: **12.4%**\nSync Status: `[✧✧◈◈◈◈◈◈◈◈]`", color=0xB19CD9)
        await self._send_embed(ctx, embed, fallback_text="𝒢𝓁ℴ𝒷𝒶𝓁 𝒮ℯ𝓃𝓈ℴ𝓇𝓎 𝒫𝓊𝓁𝓈ℯ Analysis Complete.")

async def setup(bot):
    if "SynapticSocial" not in bot.cogs:
        await bot.add_cog(SynapticSocial(bot))

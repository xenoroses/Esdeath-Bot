import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone, timedelta
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class SocialEngine(commands.Cog):
    """
    Tier 5 & 6: Tension, Gameplay, and Psychological Mechanics.
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

    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

    @commands.hybrid_command(name="judgement", description="Hyacine evaluates a user dramatically.")
    async def judgement(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(user.id), 5.0)
            
            if trust > 7: verdict, threat, color = "Loyal", "Negligible", 0x2ECC71
            elif trust > 4: verdict, threat, color = "Expendable", "Low", 0xF1C40F
            else: verdict, threat, color = "Traitorous", "Severe", 0xE74C3C
                
            embed = discord.Embed(title=f"❈ 𝒥𝓊𝒹𝑔ℯ𝓂ℯ𝓃𝓉: {user.display_name}", color=color)
            if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Verdict", value=f"**{verdict}**", inline=True)
            embed.add_field(name="Threat", value=f"**{threat}**", inline=True)
            await self._send_embed(ctx, embed, fallback_text=f"𝒥𝓊𝒹𝑔ℯ𝓂ℯ𝓃𝓉 Result: **{verdict}** (Threat: {threat})")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒥𝓊𝒹𝑔ℯ𝓂ℯ𝓃𝓉 failed:** {e}")

    @commands.hybrid_command(name="fealty", description="Measures allegiance to the server.")
    async def fealty(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            tenure_days = (datetime.datetime.now(timezone.utc) - target.joined_at).days if target.joined_at else 1
            idx = min(100, int((trust * 8) + (min(20, tenure_days / 30 * 5))))
            
            embed = discord.Embed(title="✾ ℱℯ𝒶𝓁𝓉𝓎 𝒮𝓎𝓃𝒸𝒽𝓇ℴ𝓃𝒾𝓏𝒶𝓉𝒾𝄴𝓃", color=0xB19CD9)
            embed.description = f"**Loyalty Index:** {idx}/100\n**Protocol:** Synergy"
            await self._send_embed(ctx, embed, fallback_text=f"ℱℯ𝒶𝓁𝓉𝓎 Index for {target.display_name}: **{idx}/100**")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℱℯ𝒶𝓁𝓉𝓎 failed:** {e}")

    @commands.hybrid_command(name="vendetta", description="Creates a temporary rivalry lock.")
    async def vendetta(self, ctx: commands.Context, target: discord.Member):
        await ctx.defer()
        try:
            if target.id == ctx.author.id: return await ctx.send("You cannot declare a vendetta against yourself.")
            embed = discord.Embed(title="🩸 𝒱ℯ𝓃𝒹ℯтт𝒶 𝒟ℯ𝒸𝓁𝒶𝓇ℯ𝒹", description=f"{ctx.author.mention} has challenged {target.mention}.", color=0xE74C3C)
            await self._send_embed(ctx, embed, fallback_text=f"𝒱ℯ𝓃𝒹ℯтт𝒶 Declared against {target.mention}.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **Declaration Failed:** {e}")

    @commands.hybrid_command(name="clash", description="Quick skill duel mechanic.")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def clash(self, ctx: commands.Context, opponent: discord.Member):
        if opponent.bot or opponent.id == ctx.author.id: return await ctx.send("Invalid opponent.", ephemeral=True)
        await ctx.send(f"❈ {opponent.mention}, **{ctx.author.display_name}** challenges you to a clash! Type `defend` to accept.")
        
    @commands.hybrid_command(name="subvert", description="Harmless chaos interaction.")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def subvert(self, ctx: commands.Context, target: discord.Member):
        await ctx.defer()
        embed = discord.Embed(title="𖦹 𝒮𝓊𝒷𝓋ℯ𝓇𝓈𝒾ℴ𝓃 𝒜ттℯ𝓂𝓅𝓉ℯ𝒹", description=f"Outcome: Processing...", color=0x9B59B6)
        await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓊𝒷𝓋ℯ𝓇𝓈𝒾ℴ𝓃 Outcome for {target.display_name}: Unknown.")

    @commands.hybrid_command(name="aegis", description="Declares a protection pact.")
    async def aegis(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        embed = discord.Embed(title="✧ 𝒜ℯ𝑔i𝓈 ℒ𝒾𝓃𝓀 Established", description=f"{ctx.author.mention} protecting {user.mention}.", color=0x3498DB)
        await self._send_embed(ctx, embed, fallback_text=f"𝒜ℯ𝑔i𝓈 Link established for {user.display_name}.")

    @commands.hybrid_command(name="surveillance", description="Adds someone to Watchlist.")
    @commands.has_permissions(manage_messages=True)
    async def surveillance(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        embed = discord.Embed(title="⌬ 𝒯𝒶𝓇𝑔ℯ𝓉 ℒℴ𝒸𝓀ℯ𝒹", description=f"**{user.display_name}** added to high-priority watchlist.", color=0xE74C3C)
        await self._send_embed(ctx, embed, fallback_text=f"𝒯𝒶𝓇𝑔ℯ𝓉 {user.display_name} is now under Surveillance.")

async def setup(bot):
    if "SocialEngine" not in bot.cogs:
        await bot.add_cog(SocialEngine(bot))

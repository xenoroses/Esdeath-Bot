import discord
from discord.ext import commands
import json
import datetime
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
from redis_utils import rget_json, rset_json

class PrestigeEngine(commands.Cog):
    """
    Tier 4: Long-Term Hierarchical Progression and Lore.
    Hardened for multi-permission environments and hierarchy protection.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

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

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check to prevent raw Forbidden errors."""
        if not isinstance(member, discord.Member): return True
        
        error_msg = None
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟: Subject ranks equal to or above your authority."
        elif member.id == ctx.guild.owner_id:
            error_msg = "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Owner cannot be processed."
        elif member.top_role >= ctx.me.top_role:
            error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Target's rank exceeds my system permissions."

        if error_msg:
             embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
             await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
             return False
        return True

    @commands.hybrid_command(name="bestow", description="Hyacine grants a dynamic prestige title to a user.")
    @commands.has_permissions(manage_roles=True)
    async def bestow(self, ctx: commands.Context, user: discord.Member, *, title: str):
        await ctx.defer()
        if not await self._check_hierarchy(ctx, user): return
        try:
            key = f"titles:{ctx.guild.id}"
            data = await self._safe_rget(key)
            user_titles = data.get(str(user.id), [])
            if title not in user_titles: user_titles.append(title)
            data[str(user.id)] = user_titles
            await self._safe_rset(key, data)
            
            embed = discord.Embed(title="✵ 𝒫𝓇ℯ𝓈𝓉𝒾ℊℯ Bestowed", description=f"{user.mention} is now known as: **{title.upper()}**", color=0xF1C40F)
            await self._send_embed(ctx, embed, fallback_text=f"𝒫𝓇ℯ𝓈𝓉𝒾ℊℯ Bestowed: {user.display_name} = {title}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℬℯ𝓈𝓉ℴ𝓌𝒶𝓁 failed:** {e}")

    @commands.hybrid_command(name="canonize", description="Elevates a user to the Pantheon.")
    @commands.has_permissions(administrator=True)
    async def canonize(self, ctx: commands.Context, user: discord.Member, *, legacy: str):
        await ctx.defer()
        if not await self._check_hierarchy(ctx, user): return
        try:
            key = f"pantheon:{ctx.guild.id}"
            data = await self._safe_rget(key)
            pantheon = data.get("legends", {})
            pantheon[str(user.id)] = {"name": user.display_name, "legacy": legacy, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
            data["legends"] = pantheon
            await self._safe_rset(key, data)
            
            embed = discord.Embed(title="❂ ℒℯℊℯ𝓃𝒹 Canonized", description=f"{user.mention} immortalized.\nLegacy: *{legacy}*", color=0x9B59B6)
            await self._send_embed(ctx, embed, fallback_text=f"ℒℯℊℯ𝓃𝒹 Canonized: {user.display_name}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒞𝒶𝓃ℴ𝓃𝒾𝓏𝒶𝓉𝒾𝄴𝓃 failed:** {e}")

    @commands.hybrid_command(name="pantheon", description="Displays server legends.")
    async def pantheon(self, ctx: commands.Context):
        await ctx.defer()
        try:
            data = await self._safe_rget(f"pantheon:{ctx.guild.id}")
            legends = data.get("legends", {})
            if not legends: return await ctx.send("📝 The Pantheon remains empty.")
            
            embed = discord.Embed(title="❂ ℋ𝒶𝓁𝓁 ℴ𝒻 Influence", color=0x8E44AD)
            for uid, info in list(legends.items())[:10]:
                embed.add_field(name=f"✧ {info['name']}", value=f"_{info['legacy']}_", inline=False)
            await self._send_embed(ctx, embed, fallback_text="𝒫𝒶𝓃𝓉ℯℴ𝓃 of Influence Analysis Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **Retrieval failed:** {e}")

    @commands.hybrid_command(name="renown", description="Passive algorithmic prestige standing.")
    async def renown(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            base_trust = trust_scores.get(str(target.id), 5.0)
            renown_score = int(base_trust * 10)
            
            embed = discord.Embed(title=f"✵ ℛℯ𝓃ℴ𝓌𝓃: {target.display_name}", color=0x34495E)
            embed.add_field(name="Aggregate Score", value=f"**{renown_score}**", inline=True)
            await self._send_embed(ctx, embed, fallback_text=f"ℛℯ𝓃ℴ𝓌𝓃 Score: **{renown_score}**")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℛℯ𝓃ℴ𝓌𝓃 check failed:** {e}")

    @commands.hybrid_command(name="stratum", description="Displays hierarchical evolution.")
    async def stratum(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(ctx.author.id), 5.0)
            embed = discord.Embed(title=f"⟡ 𝒮𝓉𝓇𝒶т𝓊𝓂: {ctx.author.display_name}", color=0xB19CD9)
            embed.description = f"**Trust Index:** {trust:.2f}\n*Symmetry Reached.*"
            await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓉𝓇𝒶т𝓊𝓂: Trust = {trust:.2f}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **Analysis failed:** {e}")

async def setup(bot):
    if "PrestigeEngine" not in bot.cogs:
        await bot.add_cog(PrestigeEngine(bot))

import discord
from discord.ext import commands
import datetime
import json
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class TrustEngine(commands.Cog):
    """
    Tier 1 Feature: Dynamic Trust Engine.
    Evaluates behavioral trustworthiness dynamically based on age, hierarchy, and infractions.
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

    async def get_infraction_count(self, user_id, guild_id):
        key = f"infractions:{guild_id}:{user_id}"
        data = await rget_json(self.bot, key)
        if not data: return 0
        try: return len(data.get("history", []))
        except: return 0

    @commands.hybrid_command(name="trustscore", description="Calculates behavioral trust dynamically.")
    async def trustscore(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        target = user or ctx.author
        now = discord.utils.utcnow()
        
        # Calculation logic
        score = 50
        infractions = await self.get_infraction_count(target.id, ctx.guild.id)
        score -= (infractions * 15)
        
        if target.guild_permissions.administrator: score = 100
        score = max(0, min(100, score))
        
        risk_level = "Low" if score >= 75 else "Moderate" if score >= 40 else "High"
        color = 0x2ECC71 if score >= 75 else 0xF1C40F if score >= 40 else 0xE74C3C
            
        embed = discord.Embed(title=f"❂ 𝒯𝓇𝓊𝓈𝓉 𝒫𝓇ℴ𝒻𝒾𝓁ℯ: {target.display_name}", color=color)
        if target.display_avatar: embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Trust Score", value=f"**{score}/100**", inline=True)
        embed.add_field(name="Risk Level", value=f"**{risk_level}**", inline=True)
        
        await rset_json(self.bot, f"trust:{ctx.guild.id}:{target.id}", {"score": score, "risk_level": risk_level})
        
        await self._send_embed(ctx, embed, fallback_text=f"𝒯𝓇𝓊𝓈𝓉 Score for {target.display_name}: **{score}/100** | Risk: {risk_level}")

async def setup(bot):
    if "TrustEngine" not in bot.cogs:
        await bot.add_cog(TrustEngine(bot))

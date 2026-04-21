import discord
from discord.ext import commands
from typing import Literal, Optional, Union
import re

class SmartPurge(commands.Cog):
    """
    Tier 3 Feature: Advanced Smart Purge.
    Surgical message deletion filtering by bots, links, attachments, or text.
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

    @commands.hybrid_command(name="smartpurge", description="Surgically clean up channel messages based on filters.")
    @commands.has_permissions(manage_messages=True)
    async def smartpurge(self, ctx: commands.Context, limit: int = 100, filter_type: Literal["all", "bots", "links", "attachments", "contains"] = "all", *, specific_text: Optional[str] = None):
        await ctx.defer(ephemeral=True)

        if filter_type == "contains" and not specific_text:
            return await ctx.send("⌬ ⟡ **𝒴ℴ𝓊 𝓂𝓊𝓈𝓉 𝓅𝓇ℴ𝓋𝒾𝒹ℯ specific text.**", ephemeral=True)

        if limit > 500:
            return await ctx.send("⌬ ⟡ **ℒ𝒾𝓂𝒾𝓉 𝒸𝒶𝓃𝓃ℴ𝓉 ℯ𝓍𝒸ℯℯ𝒹 𝟧𝟢𝟢.**", ephemeral=True)

        def purge_check(m: discord.Message):
            if m.id == ctx.message.id: return False
            if filter_type == "all": return True
            elif filter_type == "bots": return m.author.bot
            elif filter_type == "links":
                return bool(re.search(r"http[s]?://", m.content))
            elif filter_type == "attachments":
                return len(m.attachments) > 0 or len(m.embeds) > 0
            elif filter_type == "contains":
                return specific_text.lower() in m.content.lower()
            return True

        try:
            deleted = await ctx.channel.purge(limit=limit, check=purge_check)
            await ctx.send(f"✧ **𝒮𝓂𝒶𝓇𝓉 𝒫𝓊𝓇𝑔ℯ 𝒞ℴ𝓂𝓅𝓁ℯ𝓉ℯ:** Removed **{len(deleted)}** messages.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("⌬ ⟡ **𝒜𝓊𝓉𝒽ℴ𝓇𝒾𝓉𝓎 𝒟ℯ𝓃𝒾ℯ𝒟:** I lack `Manage Messages` permissions.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒫𝓊𝓇𝑔ℯ ℐ𝓃𝓉ℯ𝓇𝓇𝓊𝓅тℯ𝒹:** {e}", ephemeral=True)

async def setup(bot):
    if "SmartPurge" not in bot.cogs:
        await bot.add_cog(SmartPurge(bot))

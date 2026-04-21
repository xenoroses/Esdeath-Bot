import discord
from discord.ext import commands
import json
import datetime
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class ScheduleEngine(commands.Cog):
    """
    Tier 12: Recurring Task Management and Cycle Automation.
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

    @commands.hybrid_group(name="schedule", description="Manage recurring temporal tasks.")
    @commands.has_permissions(administrator=True)
    async def schedule(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
             await ctx.send_help(ctx.command)

    @schedule.command(name="list", description="List active orbital tasks.")
    async def list_schedule(self, ctx: commands.Context):
        key = f"schedule:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or []
        if not data: return await ctx.send("No orbital cycles scheduled.", ephemeral=True)
        embed = discord.Embed(title="⏰ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ", color=0x3498DB)
        for task in data:
            embed.add_field(name=f"Task: {task.get('name')}", value=f"Interval: `{task.get('interval')}`", inline=False)
        await self._send_embed(ctx, embed, fallback_text="𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ summarized.")

    @schedule.command(name="clear", description="Purge all temporal tasks.")
    async def clear_schedule(self, ctx: commands.Context):
        await rset_json(self.bot, f"schedule:{ctx.guild.id}", [])
        await ctx.send("✧ **𝒮𝒸𝒽ℯ𝒹𝓊𝓁ℯ 𝒱𝒶𝓅ℴ𝓇𝒾𝓏ℯ𝒹.** All cycles terminated.")

async def setup(bot):
    if "ScheduleEngine" not in bot.cogs:
        await bot.add_cog(ScheduleEngine(bot))

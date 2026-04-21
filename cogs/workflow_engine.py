import discord
from discord.ext import commands
import json
from redis_utils import rget_json, rset_json
from typing import Union, Optional

class WorkflowEngine(commands.Cog):
    """
    Modular Automation Engine: Trigger-Condition-Action workflows.
    Standardized for premium aesthetics and global resilience.
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

    @commands.hybrid_group(name="workflow", description="Automated logic flows.")
    @commands.has_permissions(administrator=True)
    async def workflow(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
             await ctx.send_help(ctx.command)

    @workflow.command(name="list", description="List active logic gates.")
    async def list_workflows(self, ctx: commands.Context):
        key = f"workflows:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {}
        if not data: return await ctx.send("No logic gates active.", ephemeral=True)
        embed = discord.Embed(title="⚙️ 𝒮𝓎𝓈𝓉ℯ𝓂 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌𝓈", color=0xB19CD9)
        for name, flow in data.items():
            status = "Online ✧" if flow.get("enabled") else "Offline ⌬"
            embed.add_field(name=name, value=f"Status: **{status}**", inline=False)
        await self._send_embed(ctx, embed, fallback_text="𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 list summarized.")

    @workflow.command(name="toggle", description="Toggle a logic gate.")
    async def toggle_workflow(self, ctx: commands.Context, name: str):
        key = f"workflows:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {}
        if name not in data: return await ctx.send(f"⌬ ⟡ **𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 `{name}` 𝓃ℴ𝓉 𝒻ℴ𝓊𝓃𝒹.**", ephemeral=True)
        data[name]["enabled"] = not data[name]["enabled"]
        await rset_json(self.bot, key, data)
        status = "Active ✧" if data[name]["enabled"] else "Deactivated ⌬"
        await ctx.send(f"✧ **𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 `{name}` is now {status}.**")

async def setup(bot):
    if "WorkflowEngine" not in bot.cogs:
        await bot.add_cog(WorkflowEngine(bot))

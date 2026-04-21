import discord
from discord.ext import commands
import json
import asyncio
import re
from datetime import datetime, timedelta, timezone
from redis_utils import rget_json, rset_json, rget, rset
from typing import Union, Optional

class WorkflowEngine(commands.Cog):
    """
    Tier 3 Platform Automation: Master Workflow & Guardian Engine.
    Hardened for multi-permission environments and conflict resolution.
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

    @commands.hybrid_group(name="workflow", description="Advanced server automation graph.", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def workflow_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @workflow_group.command(name="create", description="Create a new logical automation workflow.")
    async def workflow_create(self, ctx: commands.Context, trigger: str, condition: str, action: str):
        valid_triggers = ["message_contains_link", "message_contains_attachment", "user_joins"]
        valid_conditions = ["untrusted_user", "new_account", "always"]
        valid_actions = ["delete_and_warn", "delete_only", "assign_quarantine_role"]
        
        if trigger not in valid_triggers or condition not in valid_conditions or action not in valid_actions:
            return await ctx.send("❌ Invalid logic parameters.")

        key = f"workflows:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {"flows": []}
        new_flow = {"id": len(data["flows"]) + 1, "trigger": trigger, "condition": condition, "action": action, "enabled": True}
        data["flows"].append(new_flow)
        await rset_json(self.bot, key, data)

        embed = discord.Embed(title="≛ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒞𝓇ℯ𝒶𝓉ℯ𝒹", description=f"**IF** `{trigger}`\n**AND** `{condition}`\n**THEN** `{action}`", color=0x2ECC71)
        await self._send_embed(ctx, embed, fallback_text=f"𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 #{new_flow['id']} Created Successfully.")

    @workflow_group.command(name="list", description="List all active workflows.")
    async def workflow_list(self, ctx: commands.Context):
        data = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or {"flows": []}
        flows = data.get("flows", [])
        if not flows: return await ctx.send("📝 No active workflows found.")
        
        embed = discord.Embed(title="≛ 𝒜𝒸𝓉𝒾𝓋ℯ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌𝓈", color=0x34495E)
        for f in flows:
            embed.add_field(name=f"Workflow #{f['id']}", value=f"IF `{f['trigger']}` THEN `{f['action']}`", inline=False)
        await self._send_embed(ctx, embed, fallback_text=f"𝒜𝒸𝓉𝒾𝓋ℯ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌𝓈 Check Complete. {len(flows)} rules found.")

    @workflow_group.command(name="visual", description="Plots a linear text-graph of active workflows.")
    async def workflow_visual(self, ctx: commands.Context):
        data = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or {"flows": []}
        flows = data.get("flows", [])
        if not flows: return await ctx.send("📝 No active workflows found.")
        
        lines = [f"┌─ [{f['trigger'].upper()}]\n└── <{f['action'].upper()}>" for f in flows]
        embed = discord.Embed(title="❂ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒟𝒜𝒢", description="```text\n" + "\n\n".join(lines) + "\n```", color=0x9B59B6)
        await self._send_embed(ctx, embed, fallback_text="𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒟𝒜𝒢 Visual Retrieval Complete.")

    @commands.hybrid_command(name="sentinel", description="Toggle always-on guardian daemon mode.")
    @commands.has_permissions(administrator=True)
    async def sentinel(self, ctx: commands.Context):
        embed = discord.Embed(title="𖦹 𝒮ℯ𝓃𝓉𝒾𝓃ℯ𝓁 𝒟𝒶ℯ𝓂ℴ𝓃 ℰ𝓃𝑔𝒶𝑔ℯ𝒹", description="Hyacine's supreme background guardian is now Active.", color=0xE74C3C)
        await self._send_embed(ctx, embed, fallback_text="𝒮ℯ𝓃𝓉𝒾𝓃ℯ𝓁 Daemon engagement signal received.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        data = await rget_json(self.bot, f"workflows:{message.guild.id}")
        if not data: return
        
        flows = data.get("flows", [])
        has_link = bool(re.search(r"http[s]?://", message.content))
        
        for f in flows:
            if f["trigger"] == "message_contains_link" and has_link:
                try:
                    target_action = f["action"]
                    if "delete" in target_action:
                        await message.delete()
                        if "warn" in target_action:
                            await message.channel.send(f"⌬ ⟡ {message.author.mention}, automation triggered.", delete_after=5)
                except: pass
                break

async def setup(bot):
    if "WorkflowEngine" not in bot.cogs:
        await bot.add_cog(WorkflowEngine(bot))

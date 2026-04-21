import discord
from discord.ext import commands
import asyncio
import json
import re
from redis_utils import rget_json, rset_json, rappend
from typing import Union, Optional

class AutomodEngine(commands.Cog):
    """
    Declarative Automod Engine.
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

    async def _safe_regex_match(self, pattern, content):
        try:
            match = await asyncio.wait_for(asyncio.to_thread(re.search, pattern, content), timeout=0.1)
            return bool(match)
        except:
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if message.author.guild_permissions.administrator: return
        key = f"automod_rules:{message.guild.id}"
        data = await rget_json(self.bot, key)
        if not data: return
        rules = data.get("rules", [])
        content = message.content
        for rule in rules:
            if rule.get("type") == "regex" and await self._safe_regex_match(rule.get("pattern", ""), content):
                await self.execute_action(message, rule.get("action"), rule)
                break

    async def execute_action(self, message: discord.Message, action: str, rule: dict):
        try:
            if action == "delete":
                await message.delete()
            elif action == "warn":
                try:
                    await message.channel.send(f"⌬ {message.author.mention}, **𝓉𝓇𝒶𝓃𝓈𝓂𝒾𝓈𝓈𝒾ℴ𝓃 𝒷𝓇ℯ𝒶𝒸𝒽 𝒹ℯ𝓉ℯ𝒸𝓉ℯ𝒹.** Message vaporized.", delete_after=10)
                except: pass
                await message.delete()
            infraction_key = f"infractions:{message.guild.id}:{message.author.id}"
            entry = {"action": action, "rule_id": rule.get("id", "?"), "timestamp": int(discord.utils.utcnow().timestamp()), "trigger": "automod"}
            await rappend(self.bot, infraction_key, json.dumps(entry))
        except: pass

    @commands.hybrid_group(name="automod", description="Configure server automod rules.")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
             await ctx.send_help(ctx.command)

    @automod.command(name="add-rule", description="Add a pattern rule.")
    async def add_rule(self, ctx: commands.Context, action: str, *, regex_pattern: str):
        if action.lower() not in ["delete", "warn"]:
            return await ctx.send("⌬ ⟡ **ℐ𝓃𝓋𝒶𝓁𝒾𝒹 𝒶𝒸𝓉𝒾ℴ𝓃.**", ephemeral=True)
        try: re.compile(regex_pattern)
        except re.error: return await ctx.send("⌬ ⟡ **ℐ𝓃𝓋𝒶𝓁𝒾𝒹 𝓇ℯℊℯ𝓍.**", ephemeral=True)
        key = f"automod_rules:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {"rules": []}
        new_rule = {"id": len(data["rules"]) + 1, "type": "regex", "pattern": regex_pattern, "action": action.lower()}
        data["rules"].append(new_rule)
        await rset_json(self.bot, key, data)
        await ctx.send(f"✧ **ℛ𝓊𝓁ℯ 𝒜𝒹𝒹ℯ𝒹:** Added rule **#{new_rule['id']}**.")

    @automod.command(name="list", description="List automod rules.")
    async def list_rules(self, ctx: commands.Context):
        key = f"automod_rules:{ctx.guild.id}"
        data = await rget_json(self.bot, key)
        if not data or not data.get("rules"): return await ctx.send("No automod rules configured.", ephemeral=True)
        rules = data.get("rules", [])
        embed = discord.Embed(title="🛡️ 𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒜𝓊𝓉ℴ𝓂ℴ𝒹 𝒢𝓊𝒶𝓇𝒹𝒾𝒶𝓃", color=0x2B2D31)
        for r in rules:
            embed.add_field(name=f"Rule #{r.get('id', '?')} | {r.get('action').upper()}", value=f"Pattern: `{r.get('pattern')}`", inline=False)
        await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒜𝓊𝓉ℴ𝓂ℴ𝒹 Guardian Protocols: {len(rules)} active.")

    @automod.command(name="remove", description="Remove rule by ID.")
    async def remove_rule(self, ctx: commands.Context, rule_id: int):
        key = f"automod_rules:{ctx.guild.id}"
        data = await rget_json(self.bot, key)
        if not data: return await ctx.send("No automod rules configured.", ephemeral=True)
        initial_len = len(data["rules"])
        data["rules"] = [r for r in data["rules"] if r.get("id") != rule_id]
        if len(data["rules"]) == initial_len:
            return await ctx.send(f"⌬ ⟡ **ℛ𝓊𝓁ℯ #{rule_id} 𝓃ℴ𝓉 𝒻ℴ𝓊𝓃𝒹.**", ephemeral=True)
        await rset_json(self.bot, key, data)
        await ctx.send(f"✧ **ℛ𝓊𝓁ℯ 𝒱𝒶𝓅ℴ𝓇𝒾𝓏ℯ𝒹:** Removed rule **#{rule_id}**.")

async def setup(bot):
    if "AutomodEngine" not in bot.cogs:
        await bot.add_cog(AutomodEngine(bot))

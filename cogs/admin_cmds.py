import discord
from discord.ext import commands
from contextlib import redirect_stdout
import time
import psutil
import platform
import asyncio
import json
from redis_utils import rget_json, rset_json
from typing import Union, Optional

async def is_bot_admin(ctx):
    if await ctx.bot.is_owner(ctx.author): return True
    admins = await rget_json(ctx.bot, "bot_admins") or []
    return ctx.author.id in admins

class OwnerCmds(commands.Cog):
    """
    Bot Owner and Global Administrator commands.
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

    async def _send_error(self, ctx, text):
        embed = discord.Embed(description=f"⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇:** {text}", color=0x2B2D31)
        await self._send_embed(ctx, embed, ephemeral=True, fallback_text=f"𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: {text}")

    async def _send_success(self, ctx, text, ephemeral=False):
        embed = discord.Embed(description=f"✧ {text}", color=0x9B59B6)
        await self._send_embed(ctx, embed, ephemeral=ephemeral, fallback_text=f"𝒮𝓊𝒸𝒸ℯ𝓈𝓈: {text}")

    @commands.hybrid_command(name="addadmin", description="Give global Bot Admin privileges.")
    @commands.is_owner()
    async def addadmin(self, ctx: commands.Context, user: discord.User):
        await ctx.defer(ephemeral=True)
        try:
            admins = await rget_json(self.bot, "bot_admins") or []
            if user.id in admins: return await self._send_error(ctx, f"**{user.display_name}** is already an admin.")
            admins.append(user.id)
            await rset_json(self.bot, "bot_admins", admins)
            await self._send_success(ctx, f"Granted global Bot Admin privileges to **{user.mention}**.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to save admin: {e}")

    @commands.hybrid_command(name="removeadmin", description="Revoke global Bot Admin privileges.")
    @commands.is_owner()
    async def removeadmin(self, ctx: commands.Context, user: discord.User):
        await ctx.defer(ephemeral=True)
        try:
            admins = await rget_json(self.bot, "bot_admins") or []
            if user.id not in admins: return await self._send_error(ctx, f"**{user.display_name}** is not an admin.")
            admins.remove(user.id)
            await rset_json(self.bot, "bot_admins", admins)
            await self._send_success(ctx, f"𝒮𝓉𝓇𝒾𝓅𝓅ℯ𝒹 ℬℴ𝓉 𝒜𝒹𝓂𝒾𝓃 𝓅𝓇𝒾𝓋𝒾𝓁ℯ𝑔ℯ𝓈 𝒻𝓇ℴ𝓂 **{user.mention}**.")
        except Exception as e:
            await self._send_error(ctx, f"Failed to remove admin: {e}")

    @commands.hybrid_command(name="sync", description="Synchronize command tree.")
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context, scope: str = "guild"):
        await ctx.defer(ephemeral=True)
        try:
            if scope.lower() == "global":
                synced = await self.bot.tree.sync()
            else:
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
            await self._send_success(ctx, f"Synced `{len(synced)}` gates to **this Sector**.", ephemeral=True)
        except Exception as e:
            await self._send_error(ctx, f"Sync Failure: {e}")

async def setup(bot):
    if "OwnerCmds" not in bot.cogs:
        await bot.add_cog(OwnerCmds(bot))

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


# --- CUSTOM BOT ADMIN CHECK ---
async def is_bot_admin(ctx):
    # Bot owner always allowed
    if await ctx.bot.is_owner(ctx.author):
        return True

    # Check Resource Cache for global bot admins (Standardized)
    admins = await rget_json(ctx.bot, "bot_admins") or []
    return ctx.author.id in admins


class OwnerCmds(commands.Cog):
    """
    Bot Owner and Global Administrator commands.
    Hardened for multi-permission environments.
    """

    def __init__(self, bot):
        self.bot = bot

    # --- INTERNAL HELPERS ---
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

    async def _send_error(self, ctx, text):
        embed = discord.Embed(
            description=f"⌬ ⟡ **{text}**",
            color=0x2B2D31
        )
        await self._send_embed(ctx, embed, ephemeral=True, fallback_text=f"𝒮𝓎𝓈𝓉ℯ𝓂 ℰ𝓇𝓇ℴ𝓇: {text}")

    async def _send_success(self, ctx, text, ephemeral=False):
        embed = discord.Embed(
            description=f"✧ ✦ **{text}**",
            color=0x9B59B6
        )
        await self._send_embed(ctx, embed, ephemeral=ephemeral, fallback_text=f"𝒮𝓊𝒸𝒸ℯ𝓈𝓈: {text}")

    # --- BOT ADMIN MANAGEMENT ---

    @commands.hybrid_command(
        name="addadmin",
        description="Give a user global Bot Admin privileges."
    )
    @commands.is_owner()
    async def addadmin(self, ctx: commands.Context, user: discord.User):
        await ctx.defer(ephemeral=True)

        if not self.bot.redis:
            return await self._send_error(
                ctx,
                "Memory offline. Cannot save admin."
            )

        try:
            admins = await rget_json(self.bot, "bot_admins") or []

            if user.id in admins:
                return await self._send_error(
                    ctx,
                    f"**{user.display_name}** 𝒾𝓈 𝒶𝓁𝓇ℯ𝒶𝒹𝓎 𝒶 ℬℴ𝓉 𝒜𝒹𝓂𝒾𝓃."
                )

            admins.append(user.id)
            await rset_json(self.bot, "bot_admins", admins)

            await self._send_success(
                ctx,
                f"Granted global Bot Admin privileges to **{user.mention}**."
            )

        except Exception as e:
            await self._send_error(ctx, f"Failed to save admin: {e}")

    @commands.hybrid_command(
        name="removeadmin",
        description="Revoke global Bot Admin privileges."
    )
    @commands.is_owner()
    async def removeadmin(self, ctx: commands.Context, user: discord.User):
        await ctx.defer(ephemeral=True)

        if not self.bot.redis:
            return await self._send_error(
                ctx,
                "Memory offline. Cannot remove admin."
            )

        try:
            admins = await rget_json(self.bot, "bot_admins") or []

            if user.id not in admins:
                return await self._send_error(
                    ctx,
                    f"**{user.display_name}** 𝒾𝓈 𝓃ℴ𝓉 𝒶 ℬℴ𝓉 𝒜𝒹𝓂𝒾𝓃."
                )

            admins.remove(user.id)
            await rset_json(self.bot, "bot_admins", admins)

            await self._send_success(
                ctx,
                f"𝒮𝓉𝓇𝒾𝓅𝓅ℯ𝒹 ℬℴ𝓉 𝒜𝒹𝓂𝒾𝓃 𝓅𝓇𝒾𝓋𝒾𝓁ℯ𝑔ℯ𝓈 𝒻𝓇ℴ𝓂 **{user.mention}**."
            )

        except Exception as e:
            await self._send_error(ctx, f"Failed to remove admin: {e}")

    @commands.hybrid_command(name="health", description="Check bot health status.")
    @commands.check(is_bot_admin)
    async def health(self, ctx: commands.Context):
        await ctx.defer()

        # Redis status
        redis_status = "⌬ **𝒟𝒾𝓈𝒸ℴ𝓃𝓃ℯ𝒸𝓉ℯ𝒹**"
        if getattr(self.bot, 'redis', None):
            try:
                await asyncio.wait_for(self.bot.redis.ping(), timeout=2.0)
                redis_status = "✧ **𝒞ℴ𝓃𝓃ℯ𝒸𝓉ℯ𝒹**"
            except:
                redis_status = "⌬ **𝒟𝒾𝓈𝒸ℴ𝓃𝓃ℯ𝒸𝓉ℯ𝒹**"

        # API latency
        latency = round(self.bot.latency * 1000, 2) if self.bot.latency else "N/A"

        # Uptime
        uptime = time.time() - self.bot.start_time if hasattr(self.bot, 'start_time') else 0
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"

        embed = discord.Embed(
            title="𖦹 ℋ𝓎𝒶𝒸𝒾𝓃ℯ ℋℯ𝒶𝓁𝓉ℋ 𝒮𝓉𝒶𝓉𝓊𝓈",
            color=0x9B59B6
        )
        embed.add_field(name="Redis", value=redis_status, inline=True)
        embed.add_field(name="API Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        
        await self._send_embed(ctx, embed, fallback_text=f"ℋℯ𝒶𝓁𝓉ℋ: {uptime_str} | Latency: {latency}ms | Redis: {redis_status}")

    @commands.hybrid_command(name="sync", description="Synchronize the command tree for immediate updates.")
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context, scope: str = "guild"):
        await ctx.defer(ephemeral=True)
        try:
            if scope.lower() == "global":
                synced = await self.bot.tree.sync()
                msg = f"Synced `{len(synced)}` gates across the **Global Nexus**."
            else:
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
                msg = f"Synced `{len(synced)}` gates to **this Sector**."
            
            await self._send_success(ctx, msg, ephemeral=True)
        except Exception as e:
            await self._send_error(ctx, f"Sync Failure: {e}")


async def setup(bot):
    if "OwnerCmds" not in bot.cogs:
        await bot.add_cog(OwnerCmds(bot))

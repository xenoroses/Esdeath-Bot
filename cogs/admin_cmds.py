import discord
import asyncio
from discord.ext import commands
import json
import io
import textwrap
import traceback
from contextlib import redirect_stdout


# --- CUSTOM BOT ADMIN CHECK ---
async def is_bot_admin(ctx):
    # Bot owner always allowed
    if await ctx.bot.is_owner(ctx.author):
        return True

    # Check Redis for global bot admins
    if getattr(ctx.bot, "cache", None):
        try:
            cached = await ctx.bot.cache.get("bot_admins")
            if cached:
                # cache layer decodes bytes automatically
                admins = json.loads(cached)
                return ctx.author.id in admins
        except Exception as e:
            print(f"Admin check error: {e}")

    return False


class OwnerCmds(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # --- INTERNAL HELPERS ---

    async def _send_error(self, ctx, text):
        embed = discord.Embed(
            description=f"⌬ ⟡ **{text}**",
            color=0x2B2D31
        )
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_success(self, ctx, text, ephemeral=False):
        embed = discord.Embed(
            description=f"✧ ✦ **{text}**",
            color=0x9B59B6
        )
        await ctx.send(embed=embed, ephemeral=ephemeral)

    # --- BOT ADMIN MANAGEMENT ---

    @commands.hybrid_command(
        name="addadmin",
        description="Give a user global Bot Admin privileges."
    )
    @commands.is_owner()
    async def addadmin(self, ctx: commands.Context, user: discord.User):

        if not self.bot.redis:
            return await self._send_error(
                ctx,
                "Memory offline. Cannot save admin."
            )

        try:
            cached = await self.bot.redis.get("bot_admins")

            admins = json.loads(
                cached.decode("utf-8") if isinstance(cached, bytes) else cached
            ) if cached else []

            if user.id in admins:
                return await self._send_error(
                    ctx,
                    f"**{user.display_name}** is already a Bot Admin."
                )

            admins.append(user.id)

            await self.bot.redis.set(
                "bot_admins",
                json.dumps(admins)
            )

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

        if not self.bot.redis:
            return await self._send_error(
                ctx,
                "Memory offline. Cannot remove admin."
            )

        try:
            cached = await self.bot.redis.get("bot_admins")

            admins = json.loads(
                cached.decode("utf-8") if isinstance(cached, bytes) else cached
            ) if cached else []

            if user.id not in admins:
                return await self._send_error(
                    ctx,
                    f"**{user.display_name}** is not a Bot Admin."
                )

            admins.remove(user.id)

            await self.bot.redis.set(
                "bot_admins",
                json.dumps(admins)
            )

            await self._send_success(
                ctx,
                f"Stripped Bot Admin privileges from **{user.mention}**."
            )

        except Exception as e:
            await self._send_error(ctx, f"Failed to remove admin: {e}")

    @commands.hybrid_command(name="health", description="Check bot health status.")
    @commands.check(is_bot_admin)
    async def health(self, ctx: commands.Context):
        import time
        import psutil
        import platform

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
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

        # Extension count
        ext_count = len(self.bot.extensions)

        embed = discord.Embed(
            title="𖦹 ℋ𝓎𝒶𝒸𝒾𝓃𝓉𝒽ℯ ℋℯ𝒶𝓁𝓉𝒽 𝒮𝓉𝒶𝓉𝓊𝓈",
            color=0x9B59B6
        )
        embed.add_field(name="Redis", value=redis_status, inline=True)
        embed.add_field(name="API Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Extensions", value=str(ext_count), inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Discord.py", value=discord.__version__, inline=True)

        await ctx.send(embed=embed)


async def setup(bot):
    if "OwnerCmds" not in bot.cogs:
        await bot.add_cog(OwnerCmds(bot))

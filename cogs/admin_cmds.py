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
    if getattr(ctx.bot, "redis", None):
        try:
            cached = await ctx.bot.redis.get("bot_admins")
            if cached:
                decoded = cached.decode("utf-8") if isinstance(cached, bytes) else cached
                admins = json.loads(decoded)
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
            description=f"❌ | {text}",
            color=0x2B2D31
        )
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_success(self, ctx, text, ephemeral=False):
        embed = discord.Embed(
            description=f"✅ | {text}",
            color=0x2ECC71
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

    # --- EVAL COMMAND ---

    @commands.hybrid_command(
        name="eval",
        description="Evaluate raw Python code.",
        hidden=True
    )
    @commands.check(is_bot_admin)
    async def eval_cmd(self, ctx: commands.Context, *, body: str = None):

        if body is None:
            return await ctx.send("Provide code to evaluate.")

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "discord": discord,
            "_": self.bot.last_result
        }

        env.update({
            "asyncio": asyncio,
            "datetime": __import__("datetime"),
        })

        # Remove triple-backtick formatting if present
        if body.startswith("```") and body.endswith("```"):
            body = "\n".join(body.split("\n")[1:-1])
        else:
            body = body.strip("` \n")

        # Wrap code inside async function
        to_compile = (
            "async def func():\n"
            + textwrap.indent(body, "  ")
        )

        stdout = io.StringIO()

        try:
            exec(to_compile, env)

        except Exception as e:
            return await ctx.send(
                f"```py\n{e.__class__.__name__}: {e}\n```"
            )

        func = env["func"]

        try:
            with redirect_stdout(stdout):
                ret = await asyncio.wait_for(func(), timeout=10)

        except Exception as e:

            value = stdout.getvalue()

            # Full traceback only in terminal
            print(traceback.format_exc())

            clean_error = f"{e.__class__.__name__}: {e}"

            await ctx.send(
                f"```py\n{value}{clean_error}\n```"
            )

        else:

            value = stdout.getvalue()

            try:
                await ctx.message.add_reaction("✅")
            except Exception:
                pass

            if ret is None:
                if value:
                    self.bot.last_result = value
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self.bot.last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")


async def setup(bot):
    await bot.add_cog(OwnerCmds(bot))
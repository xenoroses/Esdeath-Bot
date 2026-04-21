import discord
from discord.ext import commands
import time
import json
from redis_utils import rget_json, rset_json, rdelete
from typing import Union, Optional

class AFKCommands(commands.Cog):
    """
    Premium AFK System.
    Provides non-intrusive AFK tracking with premium aesthetics.
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

    async def get_afk_data(self, user_id, guild_id):
        return await rget_json(self.bot, f"afk:{guild_id}:{user_id}")

    @commands.hybrid_command(name="afk", description="Set yourself as AFK.")
    async def afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        await ctx.defer()
        data = {"reason": reason[:200], "timestamp": int(time.time()), "setter": ctx.author.id}
        await rset_json(self.bot, f"afk:{ctx.guild.id}:{ctx.author.id}", data)

        embed = discord.Embed(title="✧ 𝒟ℴ𝓇𝓂𝒶𝓃𝒸𝒾ℯ ℰ𝓃𝑔𝒶𝑔ℯ𝒹", description=f"**{ctx.author.display_name}** synchronized with the AFK plane.", color=0x2B2D31)
        embed.add_field(name="Reason", value=f"`{reason[:200]}`")
        await self._send_embed(ctx, embed, fallback_text=f"𝒟ℴ𝓇𝓂𝒶𝓃𝒸𝒾ℯ ℰ𝓃𝑔𝒶𝑔ℯ𝒹: {ctx.author.display_name} is AFK.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if not self.bot.redis: return

        # Return from AFK
        author_data = await self.get_afk_data(message.author.id, message.guild.id)
        if author_data and int(time.time()) - author_data.get("timestamp", 0) > 3:
            await rdelete(self.bot, f"afk:{message.guild.id}:{message.author.id}")
            try:
                await message.channel.send(f"✧ **𝒲ℯ𝓁𝒸ℴ𝓂ℯ Back {message.author.mention}!**", delete_after=5)
            except: pass

        # Mentioned AFK
        if message.mentions:
            for mentioned in message.mentions[:3]:
                if mentioned.id == message.author.id: continue
                afk_data = await self.get_afk_data(mentioned.id, message.guild.id)
                if afk_data:
                    duration = int(time.time()) - afk_data["timestamp"]
                    mins = duration // 60
                    embed = discord.Embed(description=f"✧ **{mentioned.display_name}** is AFK ({mins}m ago).\nReason: `{afk_data['reason']}`", color=0x9B59B6)
                    try:
                        await message.reply(embed=embed, mention_author=False, delete_after=10)
                    except:
                        try: await message.channel.send(f"⌬ {mentioned.display_name} is away: {afk_data['reason']}", delete_after=10)
                        except: pass

async def setup(bot):
    if "AFKCommands" not in bot.cogs:
        await bot.add_cog(AFKCommands(bot))

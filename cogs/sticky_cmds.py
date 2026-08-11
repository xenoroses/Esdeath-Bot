import asyncio
import json
from collections import defaultdict
from discord.ext import commands, tasks
import discord
import re
from redis_utils import rget_json, rset_json, rdelete
from typing import Union, Optional

class StickyCommands(commands.Cog):
    """
    Premium Sticky Message Engine.
    Ensures persistent visibility even in high-traffic or restrictive environments.
    """
    def __init__(self, bot):
        self.bot = bot
        self.channel_locks = defaultdict(asyncio.Lock)
        self.prune_trackers.start()

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

    def cog_unload(self):
        self.prune_trackers.cancel()

    @tasks.loop(hours=24)
    async def prune_trackers(self):
        for cid in list(self.channel_locks.keys()):
            if not self.bot.get_channel(cid):
                del self.channel_locks[cid]

    @commands.hybrid_command(name="sticky", description="Set a sticky message for this channel.")
    @commands.has_permissions(manage_channels=True)
    async def sticky(self, ctx: commands.Context, *, message: str):
        key = f"sticky:{ctx.channel.id}"
        await rset_json(self.bot, key, {"message": message, "last_id": None})
        await ctx.send("✧ 𝒮𝓉𝒾𝒸𝓀𝓎 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓈ℯ𝓉 𝓅𝓇ℴ𝓉ℴ𝒸ℴ𝓁 ℯ𝓃𝑔𝒶𝑔ℯ𝒹.")

    @commands.hybrid_command(name="unsticky", description="Remove sticky message from this channel.")
    @commands.has_permissions(manage_channels=True)
    async def unsticky(self, ctx: commands.Context):
        key = f"sticky:{ctx.channel.id}"
        await rdelete(self.bot, key)
        await ctx.send("⌬ 𝒮𝓉𝒾𝒸𝓀𝓎 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓇ℯ𝓂ℴ𝓋ℯ𝒹 𝒻𝓇ℴ𝓂 𝓉𝒽𝒾𝓈 𝒸𝒽𝒶𝓃𝓃ℯ𝓁.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        key = f"sticky:{message.channel.id}"
        data = await rget_json(self.bot, key)
        if not data: return

        sticky_text = data.get("message")
        last_id = data.get("last_id")
        
        if message.channel.last_message_id == last_id: return

        async with self.channel_locks[message.channel.id]:
            if last_id:
                try:
                    old_msg = await message.channel.fetch_message(last_id)
                    await old_msg.delete()
                except: pass

            try:
                new_msg = await message.channel.send(sticky_text)
                data["last_id"] = new_msg.id
                await rset_json(self.bot, key, data)
            except: pass

async def setup(bot):
    if "StickyCommands" not in bot.cogs:
        await bot.add_cog(StickyCommands(bot))

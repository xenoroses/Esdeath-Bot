import discord
from discord.ext import commands
import time
import json
from redis_utils import rget_json, rset_json

class AFKCommands(commands.Cog):
    """
    Premium AFK System.
    Provides non-intrusive AFK tracking with ephemeral/auto-deleting warnings.
    """
    def __init__(self, bot):
        self.bot = bot

    async def get_afk_data(self, user_id, guild_id):
        key = f"afk:{guild_id}:{user_id}"
        return await rget_json(self.bot, key)

    async def set_afk_data(self, user_id, guild_id, data):
        key = f"afk:{guild_id}:{user_id}"
        await rset_json(self.bot, key, data)
            
    async def remove_afk_data(self, user_id, guild_id):
        key = f"afk:{guild_id}:{user_id}"
        if getattr(self.bot, "cache", None):
            await self.bot.cache.delete(key)
        elif getattr(self.bot, "redis", None):
            await self.bot.redis.delete(key)
        elif getattr(self.bot, "redis", None):
            await self.bot.redis.delete(key)

    @commands.hybrid_command(name="afk", description="Set yourself as AFK.")
    async def afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        # Handle manual mention parsing (e.g. `es afk <@!123> sleeping`)
        target = ctx.author
        parsed_reason = reason.strip()

        if ctx.message.mentions:
            first_mention = ctx.message.mentions[0]
            # Check if the string actually starts with a ping
            if parsed_reason.startswith(f"<@{first_mention.id}>") or parsed_reason.startswith(f"<@!{first_mention.id}>"):
                if ctx.author.guild_permissions.manage_messages:
                    target = first_mention
                    # Strip the mention from the reason
                    parsed_reason = parsed_reason.split(maxsplit=1)
                    parsed_reason = parsed_reason[1] if len(parsed_reason) > 1 else "AFK"
                else:
                    return await ctx.send("⌬ ⟡ **𝒴ℴ𝓊 𝓃ℯℯ𝒹 `ℳ𝒶𝓃𝒶ℊℯ ℳℯ𝓈𝓈𝒶ℊℯ𝓈` 𝓉ℴ 𝓈ℯ𝓉 ℴ𝓉𝒽ℯ𝓇𝓈 𝒜ℱ𝒦.**", ephemeral=True)

        if len(parsed_reason) > 200:
            parsed_reason = parsed_reason[:197] + "..."

        data = {
            "reason": parsed_reason,
            "timestamp": int(time.time()),
            "setter": ctx.author.id
        }

        await self.set_afk_data(target.id, ctx.guild.id, data)

        # Build premium embed
        embed = discord.Embed(
            description=f"**{target.display_name}** has gone AFK.",
            color=0x2B2D31
        )
        embed.add_field(name="Reason", value=f"`{parsed_reason}`", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        if target.id != ctx.author.id:
            embed.set_footer(text=f"AFK forced by {ctx.author.display_name}")

        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 1. Check if the author is returning from AFK
        author_data = await self.get_afk_data(message.author.id, message.guild.id)
        if author_data:
            # Prevent instant removal if they literally just typed the 'es afk' command
            if int(time.time()) - author_data.get("timestamp", 0) > 3:
                await self.remove_afk_data(message.author.id, message.guild.id)
                # Send a welcome back message that auto-deletes to keep chat clean
                try:
                    welcome_msg = await message.channel.send(f"Welcome back {message.author.mention}! Your AFK status has been removed.")
                    await welcome_msg.delete(delay=5)
                except:
                    pass

        # 2. Check if the messagementions any AFK users
        if message.mentions:
            for mentioned_user in set(message.mentions):
                # Don't reply if they mention themselves
                if mentioned_user.id == message.author.id:
                    continue
                    
                afk_data = await self.get_afk_data(mentioned_user.id, message.guild.id)
                if afk_data:
                    # Calculate duration
                    duration = int(time.time()) - afk_data["timestamp"]
                    mins, secs = divmod(duration, 60)
                    hours, mins = divmod(mins, 60)
                    
                    time_str = ""
                    if hours > 0: time_str += f"{hours}h "
                    if mins > 0: time_str += f"{mins}m "
                    time_str += f"ago" if hours > 0 or mins > 0 else "just now"

                    embed = discord.Embed(
                        description=f"**{mentioned_user.display_name}** went AFK {time_str}.\n\n**Reason:** `{afk_data['reason']}`",
                        color=0x7289DA
                    )
                    embed.set_author(name="AFK Notification", icon_url=mentioned_user.display_avatar.url)
                    
                    try:
                        warn_msg = await message.reply(embed=embed, mention_author=False)
                        # Auto-delete warning to prevent spam buildup
                        await warn_msg.delete(delay=10)
                    except:
                        pass
                    # Only send one AFK warning per message to avoid spamming if multiple AFK people are pinged
                    break


async def setup(bot):
    if "AFKCommands" not in bot.cogs:
        await bot.add_cog(AFKCommands(bot))

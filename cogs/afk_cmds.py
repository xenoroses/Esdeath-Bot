import discord
from discord.ext import commands
import time
import json
from redis_utils import rget_json, rset_json, rget, rset, rdelete

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
        await rdelete(self.bot, key)

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
                    parts = parsed_reason.split(maxsplit=1)
                    parsed_reason = parts[1] if len(parts) > 1 else "AFK"
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
            title="✧ 𝒟ℴ𝓇𝓂𝒶𝓃𝒸𝓎 ℰ𝓃ℊ𝒶ℊℯ𝒹",
            description=f"**{target.display_name}** 𝒽𝒶𝓈 𝓈𝓎𝓃𝒸𝒽𝓇ℴ𝓃𝒾𝓏ℯ𝒹 𝓌𝒾𝓉𝒽 𝓉𝒽ℯ 𝒜ℱ𝒦 𝓅𝓁𝒶𝓃ℯ.",
            color=0x2B2D31
        )
        embed.add_field(name="Reason", value=f"`{parsed_reason}`", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        if target.id != ctx.author.id:
            embed.set_footer(text=f"Index forced by {ctx.author.display_name}")

        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        if not self.bot.redis: return

        # 1. Check if the author is returning from AFK
        author_data = await self.get_afk_data(message.author.id, message.guild.id)
        if author_data:
            # Prevent instant removal if they literally just typed the 'es afk' command
            if int(time.time()) - author_data.get("timestamp", 0) > 3:
                # DISTRIBUTED LOCK: Prevent duplicate AFK removals/warnings
                lock_key = f"lock:afk:return:{message.author.id}"
                if await self.bot.redis.set(lock_key, "1", nx=True, ex=5):
                    await self.remove_afk_data(message.author.id, message.guild.id)
                    try:
                        welcome_msg = await message.channel.send(f"✧ **𝒲ℯ𝓁𝒸ℴ𝓂ℯ 𝒷𝒶𝒸𝓀 {message.author.mention}! 𝒜ℱ𝒦 𝓈𝓉𝒶𝓉𝓊𝓈 𝓅𝓊𝓇ℊℯ𝒹.**")
                        await welcome_msg.delete(delay=5)
                    except: pass

        # 2. Check if the message mentions any AFK users
        if message.mentions:
            # SCALE GUARD: Limit mention checking to first 3 unique mentions
            processed = 0
            for mentioned_user in set(message.mentions):
                if processed >= 3: break
                if mentioned_user.id == message.author.id: continue
                
                afk_data = await self.get_afk_data(mentioned_user.id, message.guild.id)
                if afk_data:
                    processed += 1
                    # Rate limit: Don't spam warnings if many people ping in a row
                    warn_lock = f"warn:afk:{mentioned_user.id}:{message.channel.id}"
                    if not await self.bot.redis.set(warn_lock, "1", nx=True, ex=10):
                        continue

                    duration = int(time.time()) - afk_data["timestamp"]
                    mins, secs = divmod(duration, 60)
                    hours, mins = divmod(mins, 60)
                    
                    time_str = ""
                    if hours > 0: time_str += f"{hours}h "
                    if mins > 0: time_str += f"{mins}m "
                    time_str += f"ago" if hours > 0 or mins > 0 else "just now"

                    embed = discord.Embed(
                        description=f"✦ ✧ **{mentioned_user.display_name}** 𝒹𝓇𝒾𝒻𝓉ℯ𝒹 𝒜ℱ𝒦 {time_str}.\n\n**ℛℯ𝒶𝓈ℴ𝓃:** `{afk_data['reason']}`",
                        color=0x9B59B6
                    )
                    embed.set_author(name="𝒮𝓉ℯ𝓁𝓁𝒶𝓇 𝒟ℴ𝓇𝓂𝒶𝓃𝒸𝓎 𝒩ℴ𝓉𝒾𝒸ℯ", icon_url=mentioned_user.display_avatar.url)
                    
                    try:
                        warn_msg = await message.reply(embed=embed, mention_author=False)
                        await warn_msg.delete(delay=10)
                    except: pass

async def setup(bot):
    if "AFKCommands" not in bot.cogs:
        await bot.add_cog(AFKCommands(bot))

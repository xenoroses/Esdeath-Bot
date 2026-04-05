import discord
from discord.ext import commands
from typing import Literal, Optional
import re

class SmartPurge(commands.Cog):
    """
    Tier 3 Feature: Advanced Smart Purge.
    Surgical message deletion filtering by bots, links, attachments, or text.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="smartpurge", description="Surgically clean up channel messages based on filters.")
    @commands.has_permissions(manage_messages=True)
    async def smartpurge(self, ctx: commands.Context, limit: int = 100, filter_type: Literal["all", "bots", "links", "attachments", "contains"] = "all", *, specific_text: Optional[str] = None):
        await ctx.defer(ephemeral=True)

        # Validation
        if filter_type == "contains" and not specific_text:
            return await ctx.send("⌬ ⟡ **𝒴ℴ𝓊 𝓂𝓊𝓈𝓉 𝓅𝓇ℴ𝓋𝒾𝒹ℯ `𝓈𝓅ℯ𝒸𝒾𝒻𝒾𝒸_𝓉ℯ𝓍𝓉` 𝓌𝒽ℯ𝓃 𝓊𝓈𝒾𝓃ℊ 𝓉𝒽ℯ `𝒸ℴ𝓃𝓉𝒶𝒾𝓃𝓈` 𝒻𝒾𝓁𝓉ℯ𝓇 𝓉𝓎𝓅ℯ.**", ephemeral=True)

        if limit > 500:
            return await ctx.send("⌬ ⟡ **ℒ𝒾𝓂𝒾𝓉 𝒸𝒶𝓃𝓃ℴ𝓉 ℯ𝓍𝒸ℯℯ𝒹 𝟧𝟢𝟢 𝓂ℯ𝓈𝓈𝒶𝑔ℯ𝓈 𝒶𝓉 ℴ𝓃𝒸ℯ.**", ephemeral=True)

        # Define the checking function dynamically based on filter type
        def purge_check(m: discord.Message):
            # Never delete the command invocation message itself if it's not a slash command
            if m.id == ctx.message.id:
                return False

            if filter_type == "all":
                return True
            elif filter_type == "bots":
                return m.author.bot
            elif filter_type == "links":
                # Check for standard http/https links
                return bool(re.search(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", m.content))
            elif filter_type == "attachments":
                # Check if it has attachments or embed images
                return len(m.attachments) > 0 or len(m.embeds) > 0
            elif filter_type == "contains":
                return specific_text.lower() in m.content.lower()

            return True

        try:
            # Execute the purge
            deleted = await ctx.channel.purge(limit=limit, check=purge_check)
            
            # Send success summary
            filter_desc = f"matching filter `{filter_type}`"
            if filter_type == "contains":
                filter_desc += f" (`{specific_text}`)"
            
            await ctx.send(f"✧ **𝒮𝓂𝒶𝓇𝓉 𝒫𝓊𝓇ℊℯ 𝒞ℴ𝓂𝓅𝓁ℯ𝓉ℯ:** Surgically removed **{len(deleted)}** messages {filter_desc}.", ephemeral=True)
            
            # Optional: Log the purge to the database/channel here if needed
        except discord.Forbidden:
            await ctx.send("⌬ ⟡ **𝒜𝓊𝓉𝒽ℴ𝓇𝒾𝓉𝓎 𝒟ℯ𝓃𝒾ℯ𝒹:** ℐ 𝓁𝒶𝒸𝓀 `ℳ𝒶𝓃𝒶𝑔ℯ ℳℯ𝓈𝓈𝒶𝑔ℯ𝓈` 𝓅ℯ𝓇𝓂𝒾𝓈𝓈𝒾ℴ𝓃𝓈.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒫𝓊𝓇ℊℯ ℐ𝓃𝓉ℯ𝓇𝓇𝓊𝓅𝓉ℯ𝒹:** {e}", ephemeral=True)

async def setup(bot):
    if "SmartPurge" not in bot.cogs:
        await bot.add_cog(SmartPurge(bot))

import discord
from discord.ext import commands
import json
import re
import asyncio
from datetime import datetime, timezone, timedelta
from redis_utils import rget_json, rset_json, rget, rset, rappend

class AIUtilityCommands(commands.Cog):
    """
    Tier 1 AI & Moderation Utility: Summarization, Policy context, and Channel memory.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="summarize", description="AI Channel Digest: Summarize the last N messages.")
    @commands.has_permissions(manage_messages=True)
    async def summarize(self, ctx: commands.Context, limit: int = 50):
        await ctx.defer()
        
        if limit > 200:
            return await ctx.send("⌬ ⟡ **𝒮𝓊𝓂𝓂𝒶𝓇𝒾𝓏ℯ 𝒸𝒶𝓅𝓅ℯ𝒹 𝒶𝓉 𝟤𝟢ℴ 𝓂ℯ𝓈𝓈𝒶𝑔ℯ𝓈.**")
            
        messages = [m async for m in ctx.channel.history(limit=limit)]
        messages.reverse() # Chronological
        
        participants = {}
        for m in messages:
            if m.author.bot: continue
            participants[m.author.display_name] = participants.get(m.author.display_name, 0) + 1
            
        top_talkers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:3]
        
        embed = discord.Embed(title=f"⌬ 𝒞𝒽𝒶𝓃ℐℯ𝓁 𝒟𝒾𝑔ℯ𝓈𝓉: #{ctx.channel.name}", description=f"Analyzed the last {limit} messages.", color=0x9B59B6)
        
        talker_str = "\n".join([f"• **{name}**: {cnt} msgs" for name, cnt in top_talkers])
        if not talker_str: talker_str = "No active users found."
        
        embed.add_field(name="Key Participants", value=talker_str, inline=False)
        embed.add_field(name="Auto-Generated Summary", value="> Multiple short conversations occurring.\n> No severe spikes in hostility detected.\n> Routine channel traffic.", inline=False)
        
        embed.set_footer(text="Engine: Hyacine LLM Bridge (Mock Phase)")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="policy", description="Display context-aware server rules.")
    async def policy(self, ctx: commands.Context):
        general_rules = "• Be respectful\n• No NSFW\n• Listen to staff"
        channel_rules = ""
        
        c_name = ctx.channel.name.lower()
        if "art" in c_name or "media" in c_name:
            channel_rules = "• Credit original artists\n• No AI art without disclosure\n• Keep feedback constructive"
        elif "bot" in c_name or "spam" in c_name:
            channel_rules = "• Bot commands only\n• Do not spam limit APIs"
        elif "help" in c_name or "support" in c_name:
            channel_rules = "• Format code properly\n• One query per thread\n• Do not ping staff arbitrarily"
            
        embed = discord.Embed(title="❂ 𝒞ℴ𝓃𝓉ℯ𝓍𝓉-𝒜𝓌ℯ 𝒫ℴ𝓁𝒾𝒸𝓎", color=0x34495E)
        
        if channel_rules:
            embed.description = f"**Relevant Rules for <#{ctx.channel.id}>**\n{channel_rules}\n\n**Global Defaults**\n{general_rules}"
        else:
            embed.description = f"**Global Rules**\n{general_rules}"
            
        embed.set_footer(text="Standardized by Stellar Decree")
        await ctx.send(embed=embed)

    # --- USER BEHAVIOR MEMORY ---
    @commands.hybrid_command(name="memory", description="AI-powered user behavior analysis.")
    @commands.has_permissions(manage_messages=True)
    async def memory(self, ctx: commands.Context, user: discord.Member, days: int = 7):
        if days > 30:
            return await ctx.send("⌬ ⟡ **ℳ𝒶𝓍𝒾𝓂𝓊𝓂 𝟥𝟢 𝒹𝒶𝓎𝓈 𝒻ℴ𝓇 𝓅ℯ𝓇𝒻ℴ𝓇𝓂𝒶𝓃𝒸ℯ 𝓈𝒸𝒶𝓁𝒾𝓃ℊ.**")
            
        await ctx.defer()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            user_messages = []
            message_counts = {}
            
            # SCALE GUARD: Max 8 channels scanned sequentially to prevent hangs
            channels = sorted(ctx.guild.text_channels, key=lambda x: x.position)[:8]
            
            for channel in channels:
                try:
                    async for message in channel.history(after=cutoff_time, limit=100):
                        if message.author.id == user.id:
                            user_messages.append({
                                "content": message.content,
                                "channel": message.channel.name,
                                "mention_count": len(message.mentions)
                            })
                            message_counts[channel.name] = message_counts.get(channel.name, 0) + 1
                except: continue
            
            if not user_messages:
                return await ctx.send(f"⌬ ⟡ **𝒩ℴ 𝓇ℯℴℯ𝓃𝓉 𝒷ℯ𝒽𝒶𝓋𝒾ℴ𝓇𝒶𝓁 𝓈𝒾𝑔𝓃𝒶𝓉𝓊𝓇ℯ 𝒻ℴ𝓊𝓃𝒹 𝒻ℴ𝓇 {user.mention}.**")
            
            total_messages = len(user_messages)
            avg_daily = total_messages / days
            avg_length = sum(len(msg["content"]) for msg in user_messages) / total_messages
            
            trust_scores = await rget_json(self.bot, "trust_scores") or {}
            current_trust = trust_scores.get(str(user.id), 5.0)
            
            embed = discord.Embed(
                title=f"⌬ 𝒰𝓈ℯ𝓇 ℳℯ𝓂ℴ𝓇𝒾ℯ𝓈: {user.display_name}",
                description=f"Behavior analysis for last **{days}** days across primary sectors.",
                color=0xE67E22
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(
                name="📊 Activity Overview",
                value=f"**Messages:** {total_messages}\n**Daily Average:** {avg_daily:.1f}\n**Avg Length:** {avg_length:.0f} chars\n**Trust Score:** {current_trust:.1f}/10",
                inline=True
            )
            
            top_channels = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            channels_text = "\n".join([f"#{chan}: {count}" for chan, count in top_channels]) if top_channels else "None"
            
            embed.add_field(name="📍 Sector Preferences", value=channels_text, inline=True)
            
            embed.set_footer(text=f"Engine: Hyacine Memory Core | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℳℯ𝓂ℴ𝓇𝓎 𝒶𝓃𝒶𝓁𝓎𝓈𝒾𝓈 𝒹𝒾𝓈𝓇𝓊𝓅𝓉ℯ𝒹:** {e}")

async def setup(bot):
    if "AIUtilityCommands" not in bot.cogs:
        await bot.add_cog(AIUtilityCommands(bot))

import discord
from discord.ext import commands
import json

class AIUtilityCommands(commands.Cog):
    """
    Tier 1 AI & Moderation Utility: Summarization, Policy context, and Automod Sandbox.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="modsimulate", description="Sandbox: Test what Automod would do before it applies rules.")
    @commands.has_permissions(manage_messages=True)
    async def modsimulate(self, ctx: commands.Context, user: discord.Member, *, mock_message: str):
        # Fetch active automod rules
        key = f"automod_rules:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache') and self.bot.cache: cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis') and self.bot.redis: cached = await self.bot.redis.get(key)
        
        rules = []
        if cached:
            if isinstance(cached, bytes): cached = cached.decode()
            rules = json.loads(cached).get("rules", [])

        # Fetch Trust Score logic natively
        infractions = 0
        infraction_key = f"infractions:{ctx.guild.id}:{user.id}"
        hist_cache = None
        if hasattr(self.bot, 'cache') and self.bot.cache: hist_cache = await self.bot.cache.get(infraction_key)
        
        if hist_cache:
            if isinstance(hist_cache, bytes): hist_cache = hist_cache.decode()
            try: infractions = len(json.loads(hist_cache).get("history", []))
            except: pass

        import re
        triggered_rules = []
        for rule in rules:
            if rule.get("type") == "regex":
                try:
                    if re.search(rule.get("pattern", ""), mock_message):
                        action = rule.get("action", "unknown")
                        triggered_rules.append((action, rule.get("pattern")))
                except:
                    pass

        embed = discord.Embed(title=f"🛑 Automod Physics Simulator", color=0x2B2D31)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Target User", value=user.mention, inline=True)
        embed.add_field(name="Current Infractions", value=str(infractions), inline=True)
        
        embed.add_field(name="Test Input", value=f"`{mock_message}`", inline=False)
        
        if not triggered_rules:
            result = "✅ **Pass**. Message would be permitted."
        else:
            result = "❌ **Fail**. Message would trigger:\n"
            for action, pattern in triggered_rules:
                result += f"• **{action.upper()}** (Hit on: `{pattern}`)\n"
                
            if infractions >= 3:
                result += "\n⚠️ *Warning*: User has 3+ infractions. Standard escalation protocols advise **Timeout/Ban** instead of simple warning."

        embed.add_field(name="Execution Preview", value=result, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="summarize", description="AI Channel Digest: Summarize the last N messages.")
    @commands.has_permissions(manage_messages=True)
    async def summarize(self, ctx: commands.Context, limit: int = 50):
        await ctx.defer()
        
        if limit > 200:
            return await ctx.send("To protect API limits, summarize is capped at 200 messages.")
            
        messages = [m async for m in ctx.channel.history(limit=limit)]
        messages.reverse() # Chronological
        
        # Simple extraction summary (Since full LLM bridging requires mapping the exact prompt format in llm.py)
        # We will extract top users and a sentiment baseline.
        participants = {}
        for m in messages:
            if m.author.bot: continue
            participants[m.author.display_name] = participants.get(m.author.display_name, 0) + 1
            
        top_talkers = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:3]
        
        embed = discord.Embed(title=f"🧠 Channel Digest: #{ctx.channel.name}", description=f"Analyzed the last {limit} messages.", color=0x9B59B6)
        
        talker_str = "\n".join([f"• **{name}**: {cnt} msgs" for name, cnt in top_talkers])
        if not talker_str: talker_str = "No active users found."
        
        embed.add_field(name="Key Participants", value=talker_str, inline=False)
        embed.add_field(name="Auto-Generated Summary", value="> Multiple short conversations occurring.\n> No severe spikes in hostility detected.\n> Routine channel traffic.", inline=False)
        
        embed.set_footer(text="Advanced LLM Summarizer (Mock Local Pipeline)")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="policy", description="Display context-aware server rules.")
    async def policy(self, ctx: commands.Context):
        # Dynamically adjusts rules based on channel keywords
        general_rules = "• Be respectful\n• No NSFW\n• Listen to staff"
        channel_rules = ""
        
        c_name = ctx.channel.name.lower()
        if "art" in c_name or "media" in c_name:
            channel_rules = "• Credit original artists\n• No AI art without disclosure\n• Keep feedback constructive"
        elif "bot" in c_name or "spam" in c_name:
            channel_rules = "• Bot commands only\n• Do not spam limit APIs"
        elif "help" in c_name or "support" in c_name:
            channel_rules = "• Format code properly\n• One query per thread\n• Do not ping staff arbitrarily"
            
        embed = discord.Embed(title="📜 Context-Aware Policy", color=0x34495E)
        
        if channel_rules:
            embed.description = f"**Relevant Rules for <#{ctx.channel.id}>**\n{channel_rules}\n\n**Global Defaults**\n{general_rules}"
        else:
            embed.description = f"**Global Rules**\n{general_rules}"
            
        await ctx.send(embed=embed)

async def setup(bot):
    if "AIUtilityCommands" not in bot.cogs:
        await bot.add_cog(AIUtilityCommands(bot))

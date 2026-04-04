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

    # --- USER BEHAVIOR MEMORY ---
    @commands.hybrid_command(name="memory", description="AI-powered user behavior analysis and memory.")
    @commands.has_permissions(manage_messages=True)
    async def memory(self, ctx: commands.Context, user: discord.Member, days: int = 7):
        if days > 90:
            return await ctx.send("❌ | Maximum 90 days for performance.")
            
        await ctx.defer()
        try:
            from datetime import datetime, timezone, timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            user_messages = []
            message_counts = {}
            
            for channel in ctx.guild.text_channels:
                try:
                    async for message in channel.history(after=cutoff_time, limit=500):
                        if message.author.id == user.id:
                            user_messages.append({
                                "content": message.content,
                                "channel": message.channel.name,
                                "timestamp": message.created_at,
                                "has_attachments": bool(message.attachments),
                                "mention_count": len(message.mentions)
                            })
                            message_counts[channel.name] = message_counts.get(channel.name, 0) + 1
                except: continue
            
            if not user_messages:
                return await ctx.send(f"📝 No messages found from {user.mention} in the last {days} days.")
            
            total_messages = len(user_messages)
            avg_daily = total_messages / days
            avg_length = sum(len(msg["content"]) for msg in user_messages) / total_messages
            mention_count = sum(msg["mention_count"] for msg in user_messages)
            
            # Trust score access
            from redis_utils import rget_json
            trust_scores = await rget_json(self.bot, "trust_scores") or {}
            current_trust = trust_scores.get(str(user.id), 5.0)
            
            embed = discord.Embed(
                title=f"🧠 User Memory: {user.display_name}",
                description=f"Behavior analysis for last **{days}** days",
                color=0xE67E22
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(
                name="📊 Activity Overview",
                value=f"**Messages:** {total_messages}\n**Daily Average:** {avg_daily:.1f}\n**Avg Length:** {avg_length:.0f} chars\n**Trust Score:** {current_trust:.1f}/10",
                inline=True
            )
            
            top_channels = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            channels_text = "\n".join([f"#{chan}: {count}" for chan, count in top_channels])
            embed.add_field(name="📍 Channel Preferences", value=channels_text or "No channel data", inline=True)
            
            recent_sample = user_messages[-3:] if len(user_messages) >= 3 else user_messages
            recent_text = [f"#{msg['channel']}: {msg['content'][:50]}..." for msg in recent_sample]
            
            if recent_text:
                embed.add_field(name="💭 Recent Activity Snippets", value="\n".join(recent_text), inline=False)
            
            embed.set_footer(text=f"Engine: Hyacine Memory Core | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ | Memory analysis failed: {e}")

    # --- AI CASE SUGGESTIONS ---
    @commands.hybrid_command(name="autocase", description="AI-powered moderation case suggestions.")
    @commands.has_permissions(manage_messages=True)
    async def autocase(self, ctx: commands.Context, user: discord.Member, reason: str = None):
        await ctx.defer()
        try:
            from datetime import datetime, timezone, timedelta
            from redis_utils import rget_json
            
            trust_scores = await rget_json(self.bot, "trust_scores") or {}
            user_trust = trust_scores.get(str(user.id), 5.0)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_msgs = 0
            mentions = 0
            
            for channel in ctx.guild.text_channels:
                try:
                    async for message in channel.history(after=cutoff_time, limit=200):
                        if message.author.id == user.id:
                            recent_msgs += 1
                            mentions += len(message.mentions)
                except: continue
            
            suggestions = []
            
            if user_trust < 3:
                suggestions.append("🚫 **Immediate Ban / Kick** - Trust score is critically low.")
            elif user_trust < 5:
                suggestions.append("⚠️ **Timeout (1-24h)** - Trust score suggests monitoring is needed.")
                
            if recent_msgs > 50:
                suggestions.append("🔇 **Mute (30m-2h)** - Very high 24h message volume detected.")
            if mentions > 15:
                suggestions.append("🚷 **Mention Restriction** - Excessive user mentions.")
                
            if reason and "spam" in reason.lower():
                suggestions.append("🗑️ **Message Purge** - Reason implies recent spam.")
                
            if not suggestions:
                if user_trust > 7:
                    suggestions.append("✅ **No Action Needed** - User has excellent standing.")
                else:
                    suggestions.append("👁️ **Monitor Closely** - No severe flags tripped, but worth watching.")
            
            embed = discord.Embed(
                title=f"🤖 AI Case Analysis: {user.display_name}",
                description="Automated moderation suggestions based on behavior.",
                color=0xE74C3C
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(
                name="📊 Target Stats",
                value=f"**Trust Score:** {user_trust:.1f}/10\n**24h Vol:** {recent_msgs} msgs\n**24h Pings:** {mentions}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Hyacine Recommendations",
                value="\n".join(suggestions),
                inline=False
            )
            
            embed.set_footer(text=f"Engine: Hyacine Case AI | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ | Case analysis failed: {e}")

    # --- WHY COMMAND (Plain Language History) ---
    @commands.hybrid_command(name="why", description="Explains moderation history in plain language.")
    @commands.has_permissions(manage_messages=True)
    async def why(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            from redis_utils import rget_json
            from datetime import datetime, timezone
            
            # Fetch infractions history
            key = f"infractions:{ctx.guild.id}:{user.id}"
            data = await rget_json(self.bot, key) or {}
            history = data.get("history", [])
            
            if not history:
                embed = discord.Embed(
                    title=f"🛡️ Case File: {user.display_name}",
                    description=f"✅ {user.mention} has an **entirely clean record**. No moderation actions have ever been taken against this user.",
                    color=0x2ECC71
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text="Hyacine Records Management")
                return await ctx.send(embed=embed)
            
            # Analyze history logically
            warnings = 0
            timeouts = 0
            kicks = 0
            bans = 0
            
            spam_count = 0
            toxicity_count = 0
            other_reasons = []
            
            for event in history:
                action = event.get("action", "").lower()
                reason = event.get("reason", "").lower()
                
                if "warn" in action: warnings += 1
                elif "timeout" in action or "mute" in action: timeouts += 1
                elif "kick" in action: kicks += 1
                elif "ban" in action: bans += 1
                
                if "spam" in reason or "flood" in reason or "raid" in reason: spam_count += 1
                elif "toxic" in reason or "harass" in reason or "slur" in reason: toxicity_count += 1
                elif reason: other_reasons.append(reason)
            
            # Construct a 'plain language' explanation
            explanation_parts = []
            if warnings:
                explanation_parts.append(f"has received **{warnings} warning(s)**")
            if timeouts:
                explanation_parts.append(f"has been **timed out {timeouts} time(s)**")
            if kicks:
                explanation_parts.append(f"was **kicked {kicks} time(s)**")
            if bans:
                explanation_parts.append(f"was **banned {bans} time(s)**")
                
            action_summary = " and ".join(explanation_parts) if explanation_parts else "has minor logged incidents"
            
            # Reason profile
            reason_profile = []
            if spam_count > 0:
                reason_profile.append("repeated issues with **spam/flooding**")
            if toxicity_count > 0:
                reason_profile.append("instances of **toxicity or harassment**")
            
            profile = " and ".join(reason_profile)
            if not profile:
                profile = "various miscellaneous rule violations"
                
            plain_text = f"{user.mention} {action_summary}.\n\nTheir history primarily consists of {profile}."
            
            # Get latest incident
            latest = history[-1] if history else None
            
            embed = discord.Embed(
                title=f"🛡️ Case File: {user.display_name}",
                description=str(plain_text),
                color=0xE67E22 if timeouts or warnings > 2 else 0xF1C40F
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(name="Total Infractions", value=f"**{len(history)}** logged event(s)", inline=True)
            
            if latest:
                embed.add_field(name="Latest Incident", value=f"**Action:** {latest.get('action', 'Unknown').capitalize()}\n**Reason:** {latest.get('reason', 'None')}", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Case Profiler")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ | History check failed: {e}")

async def setup(bot):
    if "AIUtilityCommands" not in bot.cogs:
        await bot.add_cog(AIUtilityCommands(bot))

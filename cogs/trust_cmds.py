import discord
from discord.ext import commands
import datetime
import json
from redis_utils import rget_json

class TrustEngine(commands.Cog):
    """
    Tier 1 Feature: Dynamic Trust Engine.
    Evaluates behavioral trustworthiness dynamically based on age, hierarchy, and infractions.
    """
    def __init__(self, bot):
        self.bot = bot

    async def get_infraction_count(self, user_id, guild_id):
        key = f"infractions:{guild_id}:{user_id}"
        data = await rget_json(self.bot, key)
        if not data:
            return 0
        try:
            return len(data.get("history", []))
        except:
            return 0

    @commands.hybrid_command(name="trustscore", description="Calculates behavioral trust dynamically.")
    async def trustscore(self, ctx: commands.Context, user: discord.Member = None):
        target = user or ctx.author
        
        now = discord.utils.utcnow()
        account_age_days = (now - target.created_at).days
        join_age_days = (now - target.joined_at).days if target.joined_at else 0
        
        # Base Score is 20
        score = 20
        signals = []
        
        # 1. Account Age (+ max 15)
        acc_score = min(15, int(account_age_days / 180) * 2)
        score += acc_score
        if account_age_days < 30:
            signals.append("🔴 Very new Discord account")
            
        # 2. Join Age (+ max 35)
        join_score = min(35, int(join_age_days / 30) * 2)
        score += join_score
        if join_age_days > 365:
            signals.append("🟢 Long-term membership")
        elif join_age_days < 7:
            signals.append("🟡 Recently joined server")
            
        # 3. Role Hierarchy (+ max 30)
        total_roles = len(ctx.guild.roles)
        # Prevent division by zero
        role_ratio = (target.top_role.position / total_roles) if total_roles > 0 else 0
        role_score = min(30, int(role_ratio * 30))
        if target.guild_permissions.administrator:
            role_score = 30
            signals.append("🟢 Server Administrator")
        elif role_ratio > 0.6:
            signals.append("🟢 High ranking role")
        score += role_score
        
        # 4. Infractions (-20 each)
        infractions = await self.get_infraction_count(target.id, ctx.guild.id)
        if infractions == 0:
            signals.append("🟢 Clean moderation history")
        else:
            score -= (infractions * 20)
            signals.append(f"🔴 {infractions} recorded automod infractions")
            
        # 5. Message Velocity Analysis (last 24h)
        message_count = 0
        mention_count = 0
        channels_used = set()
        
        # Analyze recent messages (if bot has message cache/intent)
        if ctx.guild.me.guild_permissions.read_message_history:
            for channel in ctx.guild.text_channels[:5]:  # Limit to first 5 channels for performance
                try:
                    async for message in channel.history(limit=100, after=now - datetime.timedelta(hours=24)):
                        if message.author.id == target.id:
                            message_count += 1
                            mention_count += len(message.mentions)
                            channels_used.add(channel.id)
                except:
                    continue
        
        # Message velocity scoring
        if message_count > 200:
            score -= 15
            signals.append(f"🔴 High message velocity: {message_count} messages/24h")
        elif message_count > 50:
            score -= 5
            signals.append(f"🟡 Moderate activity: {message_count} messages/24h")
        else:
            score += 5
            signals.append(f"🟢 Normal activity: {message_count} messages/24h")
            
        # Mention frequency analysis
        if mention_count > 20:
            score -= 10
            signals.append(f"🔴 High mention frequency: {mention_count} mentions/24h")
        elif mention_count > 5:
            signals.append(f"🟡 Moderate mentions: {mention_count}/24h")
            
        # Channel diversity
        channel_diversity = len(channels_used)
        if channel_diversity > 5:
            score += 5
            signals.append(f"🟢 High channel diversity: {channel_diversity} channels")
        elif channel_diversity < 2:
            score -= 5
            signals.append(f"🟡 Low channel diversity: {channel_diversity} channels")
        score = max(0, min(100, score))
        
        # Determine Risk Level
        if score >= 75:
            risk_level = "Low"
            color = 0x2ECC71 # Green
        elif score >= 40:
            risk_level = "Moderate"
            color = 0xF1C40F # Yellow
        else:
            risk_level = "High"
            color = 0xE74C3C # Red
            
        embed = discord.Embed(title=f"Trust Profile: {target.display_name}", color=color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Trust Score", value=f"**{score}/100**", inline=True)
        embed.add_field(name="Risk Level", value=f"**{risk_level}**", inline=True)
        
        # Add activity metrics
        embed.add_field(name="Activity (24h)", value=f"Messages: {message_count}\nMentions: {mention_count}\nChannels: {channel_diversity}", inline=True)
        
        signals_text = "\n".join(signals) if signals else "No significant signals."
        embed.add_field(name="Behavioral Signals", value=signals_text, inline=False)
        
        # Store trust score in Redis for 24 hours
        trust_data = {
            "score": score,
            "risk_level": risk_level,
            "signals": signals,
            "last_updated": now.isoformat(),
            "message_count": message_count,
            "mention_count": mention_count,
            "channel_diversity": channel_diversity
        }
        
        from redis_utils import rset_json
        await rset_json(self.bot, f"trust:{ctx.guild.id}:{target.id}", trust_data)
        
        embed.set_footer(text="Engine: Esdeath Trust Evaluation | Cached for 24h")
        await ctx.send(embed=embed)

async def setup(bot):
    if "TrustEngine" not in bot.cogs:
        await bot.add_cog(TrustEngine(bot))

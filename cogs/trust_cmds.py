import discord
from discord.ext import commands
import datetime
import json
from redis_utils import rget_json, rset_json

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
            signals.append("⟡ **𝒱ℯ𝓇𝓎 𝓃ℯ𝓌 𝒟𝒾𝓈𝒸ℴ𝓇𝒹 𝒶𝒸ℴ𝓊𝓃𝓉**")
            
        # 2. Join Age (+ max 35)
        join_score = min(35, int(join_age_days / 30) * 2)
        score += join_score
        if join_age_days > 365:
            signals.append("✧ **ℒℴ𝓃𝑔-𝓉ℯ𝓇𝓂 𝓂ℯ𝓂𝒷ℯ𝓇𝓈𝒽𝒾𝓅**")
        elif join_age_days < 7:
            signals.append("✵ **ℛℯ𝒸ℯ𝓃𝓉𝓁𝓎 𝒿ℴ𝒾𝓃ℯ𝒹 𝓈ℯ𝓇𝓋ℯ𝓇**")
            
        # 3. Role Hierarchy (+ max 30)
        total_roles = len(ctx.guild.roles)
        # Prevent division by zero
        role_ratio = (target.top_role.position / total_roles) if total_roles > 0 else 0
        role_score = min(30, int(role_ratio * 30))
        if target.guild_permissions.administrator:
            role_score = 30
            signals.append("✧ **𝒮ℯ𝓇𝓋ℯ𝓇 𝒜𝒹𝓂𝒾𝓃𝒾𝓈𝓉𝓇𝒶𝓉ℴ𝓇**")
        elif role_ratio > 0.6:
            signals.append("✧ **ℋ𝒾𝑔𝒽 𝓇𝒶𝓃𝓀𝒾𝓃𝑔 𝓇ℴ𝓁ℯ**")
        score += role_score
        
        # 4. Infractions (-20 each)
        infractions = await self.get_infraction_count(target.id, ctx.guild.id)
        if infractions == 0:
            signals.append("✧ **𝒞𝓁ℯ𝒶𝓃 𝓂ℴ𝒹ℯ𝓇𝒶𝓉𝒾ℴ𝓃 𝒽𝒾𝓈𝓉ℴ𝓇𝓎**")
        else:
            score -= (infractions * 20)
            signals.append(f"⟡ **{infractions} 𝓇ℯ𝒸ℴ𝓇𝒹ℯ𝒹 𝒶𝓊𝓉ℴ𝓂ℴ𝒹 𝒾𝓃𝒻𝓇𝒶𝒸𝓉𝒾ℴ𝓃𝓈**")
            
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
            signals.append(f"⟡ **ℋ𝒾𝑔𝒽 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓋ℯ𝓁ℴ𝒸𝒾𝓉𝓎: {message_count} 𝓂𝓈𝑔𝓈/𝟤𝟦𝒽**")
        elif message_count > 50:
            score -= 5
            signals.append(f"✵ **𝒫𝓊𝓁𝓈𝒾𝓃𝑔 𝒶𝒸𝓉𝒾𝓋𝒾𝓉𝓎: {message_count} 𝓂𝓈𝑔𝓈/𝟤𝟦𝒽**")
        else:
            score += 5
            signals.append(f"✧ **𝒩ℴ𝓇𝓂𝒶𝓁 𝒶𝒸𝓉𝒾𝓋𝒾𝓉𝓎: {message_count} 𝓂𝓈𝑔𝓈/𝟤𝟦𝒽**")
            
        # Mention frequency analysis
        if mention_count > 20:
            score -= 10
            signals.append(f"⟡ **ℋ𝒾𝑔𝒽 𝓂ℯ𝓃𝓉𝒾ℴ𝓃 𝒻𝓇ℯ𝓆𝓊ℯ𝓃𝒸𝓎: {mention_count} 𝓅𝒾𝓃𝑔𝓈/𝟤𝟦𝒽**")
        elif mention_count > 5:
            signals.append(f"✵ **ℳℴ𝒹ℯ𝓇𝒶𝓉ℯ 𝓂ℯ𝓃𝓉𝒾ℴ𝓃𝓈: {mention_count}/𝟤𝟦𝒽**")
            
        # Channel diversity
        channel_diversity = len(channels_used)
        if channel_diversity > 5:
            score += 5
            signals.append(f"✧ **ℋ𝒾𝑔𝒽 𝒸𝒽𝒶𝓃𝓃ℯ𝓁 𝒹𝒾𝓋ℯ𝓇𝓈𝒾𝓉𝓎: {channel_diversity} 𝓈ℯ𝒸𝓉ℴ𝓇𝓈**")
        elif channel_diversity < 2:
            score -= 5
            signals.append(f"✵ **ℒℴ𝓌 𝒸𝒽𝒶𝓃𝓃ℯ𝓁 𝒹𝒾ℋℯ𝓇𝓈𝒾𝓉𝓎: {channel_diversity} 𝓈ℯ𝒸𝓉ℴ𝓇𝓈**")
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
            
        embed = discord.Embed(title=f"❂ 𝒯𝓇𝓊𝓈𝓉 𝒫𝓇ℴ𝒻𝒾𝓁ℯ: {target.display_name}", color=color)
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
        
        await rset_json(self.bot, f"trust:{ctx.guild.id}:{target.id}", trust_data)
        
        embed.set_footer(text="Engine: Hyacine Trust Evaluation | Cached for 24h")
        await ctx.send(embed=embed)

async def setup(bot):
    if "TrustEngine" not in bot.cogs:
        await bot.add_cog(TrustEngine(bot))

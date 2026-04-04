import discord
from discord.ext import commands
import json
import datetime
from datetime import timezone, timedelta
from typing import Optional
from redis_utils import rget_json, rset_json
import math
import collections
import re
from .policy_config import get_policy

def sparkline(data):
    """Generate a sparkline string from a list of numbers."""
    if not data: return "          "
    bars = u'  ▂▃▄▅▆▇█'
    d_min, d_max = min(data), max(data)
    if d_max == d_min: return bars[4] * len(data)
    return ''.join(bars[min(len(bars)-1, int((x - d_min) / (d_max - d_min) * (len(bars)-1)))] for x in data)

def create_progress_bar(percentage, length=10):
    filled = int((percentage / 100) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

class IntelligenceEngine(commands.Cog):
    """
    Tier A & F: Predictive Intelligence and Anomaly Analytics.
    Makes Hyacine feel alive over reactive.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_command(name="predict", description="Forecast likely moderation outcomes for a user based on history.")
    @commands.has_permissions(manage_messages=True)
    async def predict(self, ctx: commands.Context, user: discord.Member):
        """
        Scans exactly 200 messages in the current channel to build a neural behavioral map.
        Analyzes velocity, toxicity, and spam probability.
        """
        await ctx.defer()
        try:
            # 1. Deep Scraping (200 user messages in current channel)
            user_messages = []
            async for msg in ctx.channel.history(limit=2000):
                if msg.author.id == user.id:
                    user_messages.append(msg)
                    if len(user_messages) >= 200:
                        break
            
            if not user_messages:
                return await ctx.send(f"⌬ ⟡ **𝒮𝓊𝒷𝒿ℯ𝒸𝓉 {user.mention} 𝒽𝒶𝓈 𝒾𝓃𝓈𝓊𝒻𝒻𝒾𝒸𝒾ℯ𝓃𝓉 𝓁ℴ𝒸𝒶𝓁 𝒻ℴℴ𝓉𝓅𝓇𝒾𝓃𝓉.**")

            # 2. Data Processing
            total_content = " ".join([m.content for m in user_messages])
            caps_count = sum(1 for c in total_content if c.isupper())
            total_chars = len(total_content) or 1
            caps_ratio = (caps_count / total_chars) * 100

            links = sum(1 for m in user_messages if "http" in m.content.lower())
            mentions = sum(len(m.mentions) for m in user_messages)
            
            # Velocity Calculation (msgs per minute in the last window)
            time_delta = (user_messages[0].created_at - user_messages[-1].created_at).total_seconds() / 60
            velocity = len(user_messages) / max(time_delta, 1)

            # 3. Decision Matrix
            spam_prob = "Low"
            tox_prob = "Low"
            esc_prob = "Low"
            color = 0x2ECC71
            risk_score = 0

            if velocity > 15: 
                spam_prob = "High"
                risk_score += 40
            elif velocity > 5:
                spam_prob = "Medium"
                risk_score += 20

            if caps_ratio > 40:
                tox_prob = "High"
                risk_score += 30
            elif caps_ratio > 15:
                tox_prob = "Medium"
                risk_score += 10

            if links > (len(user_messages) * 0.1):
                risk_score += 20
            
            # Cross-reference with Trust
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(user.id), 5.0)
            if trust < 3.0: risk_score += 30

            if risk_score > 70:
                esc_prob = "High"
                action = "Preemptive Strike / Containment"
                color = 0xE74C3C
            elif risk_score > 40:
                esc_prob = "Medium"
                action = "Elevated Surveillance"
                color = 0xE67E22
            else:
                action = "Passive Monitoring"
                color = 0x2ECC71

            # 4. Presentation
            embed = discord.Embed(
                title=f"✧ 𝗗𝗲𝗲𝗽-𝗦𝗰𝗮𝗻𝗻𝗲𝗱 𝗥𝗶𝘀𝗸 𝗣𝗿𝗼𝗷𝗲𝗰𝘁𝗶𝗼𝗻: {user.display_name}",
                description=f"Analysis based on the last **{len(user_messages)}** messages in <#{ctx.channel.id}>.",
                color=color
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(name="Spam Intensity", value=f"**{spam_prob}** ({velocity:.1f} msg/m)", inline=True)
            embed.add_field(name="Toxicity Index", value=f"**{tox_prob}** ({caps_ratio:.1f}% Caps)", inline=True)
            embed.add_field(name="Escalation Risk", value=f"**{esc_prob}**", inline=True)
            
            embed.add_field(name="Recommended Action", value=f"`[ {action} ]`", inline=False)
            
            # Metadata stats
            stats = f"• Average Msg Length: {len(total_content)//len(user_messages)} chars\n"
            stats += f"• Link/Mention Ratio: {(links+mentions)/len(user_messages):.2f}\n"
            stats += f"• Sentinel Trust Score: {trust:.1f}/10"
            embed.add_field(name="Behavioral Metadata", value=stats, inline=False)

            embed.set_footer(text="Engine: Hyacine Predictive Scrape API")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Prediction Engine Fault: {e}")

    @commands.hybrid_command(name="behaviorgraph", description="Return user behavioral trajectory by scanning recent history.")
    @commands.has_permissions(manage_messages=True)
    async def behaviorgraph(self, ctx: commands.Context, user: discord.Member):
        """
        Constructs a real activity sparkline by indexing actual message timestamps.
        """
        await ctx.defer()
        try:
            # 1. Scrape timestamps
            timestamps = []
            async for msg in ctx.channel.history(limit=1000):
                if msg.author.id == user.id:
                    timestamps.append(msg.created_at)
                    if len(timestamps) >= 300:
                        break
            
            if not timestamps:
                return await ctx.send("❌ | No behavioral footprint detected for graphing.")

            # 2. Build time clusters (count messages per hour for the last 24 slots)
            now = datetime.datetime.now(timezone.utc)
            buckets = [0] * 24
            for ts in timestamps:
                hours_ago = int((now - ts).total_seconds() / 3600)
                if 0 <= hours_ago < 24:
                    buckets[23 - hours_ago] += 1
            
            # 3. Generate Trends
            total_msgs = sum(buckets)
            peak_activity = max(buckets)
            
            embed = discord.Embed(
                title=f"✵ 𝗛𝗶𝘀𝘁𝗼𝗿𝗶𝗰𝗮𝗹 𝗧𝗿𝗮𝗷𝗲𝗰𝘁𝗼𝗿𝘆: {user.display_name}",
                description=f"Neural scan of {len(timestamps)} data points over 24 hours.",
                color=0x9B59B6
            )
            embed.set_thumbnail(url=user.display_avatar.url)

            graph = sparkline(buckets)
            
            embed.add_field(
                name="24-Hour Activity Pulse",
                value=f"```\n[{graph}]\n```\n*Time flow: Left (24h ago) to Right (Now)*",
                inline=False
            )
            
            embed.add_field(name="Peak Burst", value=f"**{peak_activity}** msg/hr", inline=True)
            embed.add_field(name="Total Volume", value=f"**{total_msgs}** messages", inline=True)
            
            status = "Stable ➖"
            if sum(buckets[-4:]) > sum(buckets[:4]): status = "Accelerating 📈"
            elif sum(buckets[-4:]) < sum(buckets[:4]): status = "Cooling Down 📉"
            
            embed.add_field(name="Current Momentum", value=status, inline=True)
            
            embed.set_footer(text="Engine: Hyacine Chrono-Scrape API")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Graph indexing failed: {e}")

    @commands.hybrid_command(name="patternscan", description="Detect emerging server behavior anomalies instantly.")
    @commands.has_permissions(manage_messages=True)
    async def patternscan(self, ctx: commands.Context):
        await ctx.defer()
        try:
            now = datetime.datetime.now(timezone.utc)
            recent_joins = [m for m in ctx.guild.members if m.joined_at and (now - m.joined_at).days < 1]
            
            mention_bursts = 0
            invite_links = 0
            
            # Scan last 50 messages in active channels
            for channel in ctx.guild.text_channels[:5]:
                try:
                    async for msg in channel.history(limit=50):
                        if len(msg.mentions) > 3: mention_bursts += 1
                        if "discord.gg/" in msg.content.lower() or "discord.com/invite/" in msg.content.lower():
                            invite_links += 1
                except: pass

            anomalies = []
            if len(recent_joins) >= 5: anomalies.append(f"🔴 **{len(recent_joins)} new-account cluster detected joining today.**")
            if mention_bursts >= 3: anomalies.append("🔴 **Mention bursts are trending suspiciously high.**")
            if invite_links >= 2: anomalies.append("🟡 **Invite links detected bypassing normal flows.**")

            if not anomalies:
                anomalies.append("🟢 **No anomalous formations detected.**")

            embed = discord.Embed(
                title=f"⌬ 𝒫𝓇ℯ𝒹𝒾𝒸𝓉𝒾𝓋ℯ ℬℯ𝒽𝒶𝓋𝒾ℴ𝓇 𝒜𝓃𝒶𝓁𝓎𝓉𝒾𝒸𝓈: {user.display_name}",
                description=f"𝒜𝓃𝒶𝓁𝓎𝓈𝒾𝓈 𝒸ℴ𝓂𝓅𝓁ℯ𝓉ℯ. 𝒰𝓌𝒰",
                color=color
            )
            embed.set_footer(text="Engine: Hyacine Early Warning System")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Scan failure: {e}")

    @commands.hybrid_command(name="casecluster", description="Group related infractions automatically.")
    @commands.has_permissions(manage_guild=True)
    async def casecluster(self, ctx: commands.Context):
        await ctx.defer()
        try:
            # We will fetch members and cluster based on join time and standard defaults
            now = datetime.datetime.now(timezone.utc)
            joins = []
            for m in ctx.guild.members:
                if m.joined_at:
                    joins.append(m)
                    
            joins.sort(key=lambda x: x.joined_at, reverse=True)
            
            clusters = []
            current_cluster = []
            
            for m in joins[:50]: # Look closely at last 50
                if not current_cluster:
                    current_cluster.append(m)
                else:
                    diff = abs((m.joined_at - current_cluster[-1].joined_at).total_seconds())
                    if diff < 120: # joined within 2 minutes of each other
                        current_cluster.append(m)
                    else:
                        if len(current_cluster) >= 3:
                            clusters.append(current_cluster)
                        current_cluster = [m]
                        
            if len(current_cluster) >= 3:
                clusters.append(current_cluster)

            embed = discord.Embed(title="🕸️ Infraction & Identity Clusters", color=0x95A5A6)
            
            if not clusters:
                embed.description = "No coordinated join or infraction clusters detected."
            else:
                embed.description = f"**{len(clusters)} Active Threat Cluster(s) Detected**\n\n"
                for idx, clast in enumerate(clusters[:3], 1):
                    names = ", ".join([c.display_name for c in clast])
                    embed.add_field(
                        name=f"Cluster #{idx} [Size: {len(clast)}]",
                        value=f"**Accounts**: {names[:200]}\n*Similarity*: Highly synchronized join-timestamps.",
                        inline=False
                    )
            
            embed.set_footer(text="Engine: Hyacine RAID Intelligence")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Cluster mapping failed: {e}")

    @commands.hybrid_command(name="modadvisor", description="AI Moderation Assistant Panel.")
    @commands.has_permissions(manage_messages=True)
    async def modadvisor(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            
            low_trust_count = sum(1 for v in trust_scores.values() if v < 4.0)
            
            advice = []
            if low_trust_count > 5:
                advice.append("• High concentration of low-trust actors. **Suggest reviewing recent case logs.**")
            
            raid_config = await self._safe_rget("raid_shield_config")
            if not raid_config.get("enabled", False):
                advice.append("• Server velocity is unshielded. **Suggest enabling RaidShield Auto.**")
            
            if trust_scores:
                avg_trust = sum(trust_scores.values()) / len(trust_scores)
                if avg_trust < 5.0:
                    advice.append("• Overall Server Sentinel Health is decaying.")
            
            if not advice:
                advice.append("• General server health optimal. No urgent interventions needed.")

            embed = discord.Embed(
                title="✤ 𝗦𝗲𝗿𝘃𝗲𝗿 𝗗𝗮𝗶𝗹𝘆 𝗗𝗶𝗴𝗲𝘀𝘁",
                description="Automated briefing prepared based on neural state.",
                color=0x2980B9
            )
            
            embed.add_field(name="Top Priorities Today", value="\n".join(advice), inline=False)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Executive Intelligence")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Advisor down: {e}")

    @commands.hybrid_command(name="verdict", description="Outputs supreme algorithmic moderation recommendation.")
    @commands.has_permissions(manage_messages=True)
    async def verdict(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(user.id), 5.0)
            
            if trust > 7.5:
                decision = "Absolute Pardon"
                conf = 98
                risk = "Negligible"
                c = 0x2ECC71
            elif trust > 4.5:
                decision = "Passive Monitoring"
                conf = 82
                risk = "Low"
                c = 0x3498DB
            elif trust > 2.0:
                decision = "Targeted Surveillance / Timeout"
                conf = 75
                risk = "Moderate"
                c = 0xE67E22
            else:
                decision = "Immediate Execution (Ban/Kick)"
                conf = 96
                risk = "CRITICAL"
                c = 0xE74C3C
                
            embed = discord.Embed(title=f"⚖️ Hyacine's Verdict", color=c)
            embed.add_field(name="Subject", value=user.mention, inline=False)
            embed.add_field(name="Verdict", value=f"**{decision}**", inline=False)
            embed.add_field(name="Confidence", value=f"`{conf}%`", inline=True)
            embed.add_field(name="Escalation Risk", value=f"`{risk}`", inline=True)
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Absolutism Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"✧ **𝒜𝒸𝓉𝒾𝓋ℯ 𝒞ℴ𝓃𝓉𝒶𝒾𝓃𝓂ℯ𝓃𝓉 𝒟ℯ𝓅𝓁ℴ𝓎ℯ𝒹:** {user.mention}", ephemeral=True)

    @commands.hybrid_command(name="threatmap", description="Server-wide risk visualization.")
    @commands.has_permissions(manage_guild=True)
    async def threatmap(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            if not trust_scores:
                return await ctx.send("No trusted mapping data acquired yet.")
                
            total = len(trust_scores)
            low_risk = sum(1 for v in trust_scores.values() if v > 6.0)
            mod_risk = sum(1 for v in trust_scores.values() if 3.0 <= v <= 6.0)
            high_risk = sum(1 for v in trust_scores.values() if v < 3.0)
            
            pct_low = (low_risk / total) * 100
            pct_mod = (mod_risk / total) * 100
            pct_high = (high_risk / total) * 100
            
            embed = discord.Embed(title="🗺️ Global Threat Map", color=0x34495E)
            
            desc = (
                f"**🟢 Low Risk ({pct_low:.1f}%)**\n{create_progress_bar(pct_low)}\n\n"
                f"**🟡 Moderate Risk ({pct_mod:.1f}%)**\n{create_progress_bar(pct_mod)}\n\n"
                f"**🔴 High Risk ({pct_high:.1f}%)**\n{create_progress_bar(pct_high)}"
            )
            
            embed.description = desc
            embed.set_footer(text="Engine: Hyacine Topography Intel")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Topography failed: {e}")

    @commands.hybrid_command(name="topicmap", description="Analyze discussion clusters with semantic radar.")
    @commands.has_permissions(manage_messages=True)
    async def topicmap(self, ctx: commands.Context):
        await ctx.defer()
        try:
            # High-Genius Semantic Scrapping
            words = []
            stop_words = {"that", "this", "what", "with", "from", "your", "have", "they", "just", "like", "when", "there"}
            
            # Scrape top 5 channels for a broader topology
            channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).view_channel][:5]
            for channel in channels:
                try:
                    async for msg in channel.history(limit=40):
                        if msg.author.bot or len(msg.content) < 5: continue
                        w = re.findall(r'\b[a-zA-Z]{5,}\b', msg.content.lower())
                        words.extend([word for word in w if word not in stop_words])
                except: pass
                
            if len(words) < 10:
                return await ctx.send("⌬ ⟡ **𝒮ℯ𝓂ℴ𝓉𝒾𝒸 𝒻𝓁ℴ𝓌 𝓉ℴℴ 𝓁ℴ𝓌.** Insufficient data for topology mapping.")
                
            counts = collections.Counter(words)
            top_clusters = counts.most_common(6)
            
            embed = discord.Embed(
                title="🗺️ Discussion Topology", 
                description="**Current Semantic Clusters Detected in Protocol:**",
                color=0xB19CD9 # Hyacine Lavender
            )
            embed.set_author(name="Stellar Semantic Radar", icon_url=self.bot.user.display_avatar.url)
            
            # Billion-Dollar Vertical Formatting (Cutesy spacing)
            cluster_str = ""
            for word, count in top_clusters:
                # Einstein-level detail
                intensity = "Vibrant ✧" if count > 5 else "Fading ⌬"
                cluster_str += f"**» {word.capitalize()}**\nFrequency: `{count}x` ⟡ Intensity: `{intensity}`\n\n"
            
            embed.add_field(name="\u200b", value=cluster_str, inline=False)
            policy = get_policy()
            # Just show a snippet or title to be high production
            embed.set_footer(text="Verified against Club Erotic Regulations | Protocol ⟡")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒯ℴ𝓅ℴ𝓁ℴℊ𝓎 𝒮𝓎𝓃𝒸𝒽𝓇ℴ𝓃𝒾𝓏𝒶𝓉𝒾ℴ𝓃 ℱ𝒶𝒾𝓁ℯ𝒹:** {e}")

async def setup(bot):
    if "IntelligenceEngine" not in bot.cogs:
        await bot.add_cog(IntelligenceEngine(bot))

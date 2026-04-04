import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone, timedelta
from redis_utils import rget_json

class LoreEngine(commands.Cog):
    """
    Tier 3: AI-Native Entertainment, Aura Scans, and Server Simulation narratives.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_command(name="aura", description="Analyzes the caller's distinct presence.")
    async def aura(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            # Simple algorithmic seed based on ID and joined date to make it consistent but unique
            joined_ts = int(target.joined_at.timestamp()) if target.joined_at else 1
            seed = target.id * joined_ts
            rng = random.Random(seed)
            
            dominance = int((trust / 10.0) * 100) + rng.randint(-10, 10)
            dominance = max(0, min(100, dominance))
            
            chaos = rng.randint(20, 95)
            if trust < 3.0: chaos = max(chaos, 80)
            
            roles = ["Strategist", "Enforcer", "Wanderer", "Catalyst", "Observer", "Instigator", "Architect"]
            narrative_role = rng.choice(roles)
            
            radius = "Expanding" if dominance > 60 else ("Stabilized" if dominance > 30 else "Contracting")
            
            embed = discord.Embed(title=f"✨ Aura Protocol Scan: {target.display_name}", color=0x9B59B6)
            embed.set_thumbnail(url=target.display_avatar.url)
            
            embed.add_field(name="Dominance", value=f"`{dominance}%`", inline=True)
            embed.add_field(name="Chaos", value=f"`{chaos}%`", inline=True)
            embed.add_field(name="Influence Radius", value=f"**{radius}**", inline=False)
            embed.add_field(name="Narrative Classification", value=f"**{narrative_role}**", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Metaphysical Sensor")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Aura read failed: {e}")

    @commands.hybrid_command(name="chronicle", description="Generates a micro-story about recent channel events.")
    @commands.has_permissions(manage_messages=True)
    async def chronicle(self, ctx: commands.Context):
        await ctx.defer()
        try:
            messages = [m async for m in ctx.channel.history(limit=100)]
            if not messages:
                return await ctx.send("The archives of this sector are entirely empty.")
                
            authors = list(set([m.author.display_name for m in messages if not m.author.bot]))
            
            rng = random.Random()
            themes = [
                "Two opposing factions locked in a fierce debate over recent shifts in the world...",
                "A tense silence was finally broken by a sudden burst of frantic strategic assembly...",
                "Words were exchanged casually, masking the cold underlying friction of the syndicate...",
                "An unexpected infiltration briefly united the scattered members of this isolated outpost..."
            ]
            
            theme = rng.choice(themes)
            
            selected_authors = rng.sample(authors, min(len(authors), 2))
            if len(selected_authors) == 2:
                involvement = f"Notably, **{selected_authors[0]}** and **{selected_authors[1]}** emerged as central figures in the ensuing developments."
            elif len(selected_authors) == 1:
                involvement = f"**{selected_authors[0]}** alone stood as the vanguard directing the flow of the entire exchange."
            else:
                involvement = "The presence of ghosts lingered as the conversation drifted into nothingness."

            embed = discord.Embed(
                title=f"📜 Chronicle: #{ctx.channel.name}",
                description=f"*{theme}*\n\n{involvement}",
                color=0x2E4053
            )
            embed.set_footer(text="Engine: Hyacine Lore Cartographer")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Chronicle generation failed: {e}")

    @commands.hybrid_command(name="wargame", description="Runs an alternate timeline scenario.")
    @commands.has_permissions(manage_messages=True)
    async def wargame(self, ctx: commands.Context):
        await ctx.defer()
        scenarios = [
            ("If the moderating hierarchy was completely purged...", "server stability drops by **84%** within **3 hours**, resulting in a critical quarantine lockout."),
            ("If RaidShield was maliciously deactivated during peak velocity...", "a cascade failure breaches the defense net within **12 minutes**, overwhelming the chat layer."),
            ("If local trust scores were inverted globally...", "a massive civil uprising triggers instantly, requiring a total wipe of recent archives."),
            ("If the Pantheon legends launched a coordinated mutiny...", "command isolation fails in **48 hours**, establishing a new ruling syndicate.")
        ]
        chosen = random.choice(scenarios)
        
        embed = discord.Embed(
            title="⚔️ Wargame: Tactical Simulation",
            description=f"**Scenario:** {chosen[0]}\n\n**Projection:**\n{chosen[1]}",
            color=0xE74C3C
        )
        embed.set_footer(text="Engine: Hyacine Tactical Predictor")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dossier", description="Constructs a fictionalized historical timeline for a user.")
    async def dossier(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            joined = target.joined_at
            if not joined:
                return await ctx.send("Temporal data missing for this target.")
                
            entry_phase = "Joined the sector under absolute silence, blending with the civilians."
            if trust > 7:
                mid_phase = "Gradually proved their combat value, rapidly ascending the biological strata."
                end_phase = "Now operates as an elite, wielding significant influence over the capital."
            elif trust > 4:
                mid_phase = "Maintained a steady existence, completing standard assignments."
                end_phase = "Currently classified as a standard asset. Predictable."
            else:
                mid_phase = "Consistently tripped internal alarms, exhibiting traitorous behavioral flags."
                end_phase = "Placed strictly on the extermination watchlist pending further observation."
                
            embed = discord.Embed(
                title=f"📂 Dossier: {target.display_name}",
                description="Historical Timeline Reconstruction",
                color=0x34495E
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            
            embed.add_field(name="[ Phase 1: Infiltration ]", value=f"_{entry_phase}_", inline=False)
            embed.add_field(name="[ Phase 2: Integration ]", value=f"_{mid_phase}_", inline=False)
            embed.add_field(name="[ Phase 3: Current State ]", value=f"_{end_phase}_", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Historical Architect")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Dossier extraction failed: {e}")

    @commands.hybrid_command(name="psychoanalyze", description="Reads organic intentions.")
    async def psychoanalyze(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        target = user or ctx.author
        
        rng = random.Random(target.id)
        motivations = ["Absolute Chaos", "Tactical Mischief", "Boredom", "Subversion", "Survival", "Self-Interest", "Devotion"]
        strategies = ["Improvised", "Calculating", "Erratic", "Non-existent", "Methodical"]
        confidences = ["Suspiciously High", "Delusional", "Calculated", "Wavering", "Nonchalant"]
        
        embed = discord.Embed(title=f"🧠 Psychoanalysis: {target.display_name}", color=0xE67E22)
        embed.add_field(name="Core Motivation", value=f"**{rng.choice(motivations)}**", inline=False)
        embed.add_field(name="Execution Strategy", value=f"**{rng.choice(strategies)}**", inline=False)
        embed.add_field(name="Confidence Level", value=f"**{rng.choice(confidences)}**", inline=False)
        
        embed.set_footer(text="Engine: Hyacine Psychological DAEMON")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="omen", description="Predicts a near-future server event.")
    @commands.cooldown(1, 1800, commands.BucketType.guild)
    async def omen(self, ctx: commands.Context):
        await ctx.defer()
        timers = ["within 45 minutes", "in the next 3 hours", "by tomorrow's rotation", "soon"]
        events = [
            "A heated ideological debate will spontaneously emerge.",
            "A dormant elite will suddenly return from the shadows.",
            "An influx of low-trust anomalies will breach the perimeter.",
            "A critical system failure will briefly destabilize the chat.",
            "An unexpected alliance will be forged between two rivals."
        ]
        
        embed = discord.Embed(
            title="👁️ Oracle's Omen",
            description=f"**Prediction:**\n{random.choice(events)}\n\n**ETA:** *{random.choice(timers)}*",
            color=0x9B59B6
        )
        embed.set_footer(text="Engine: Hyacine Prescience Array")
        await ctx.send(embed=embed)

async def setup(bot):
    if "LoreEngine" not in bot.cogs:
        await bot.add_cog(LoreEngine(bot))

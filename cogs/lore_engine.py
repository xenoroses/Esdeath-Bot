import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone, timedelta
import time
from redis_utils import rget_json

class LoreEngine(commands.Cog):
    """
    Tier 3: AI-Native Entertainment, Aura Scans, and Server Simulation narratives.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, ctx, embed, ephemeral=False, fallback_text=None):
        """Internal robust sender that handles missing 'Embed Links' permission gracefully."""
        try:
            await ctx.send(embed=embed, ephemeral=ephemeral)
        except discord.Forbidden as e:
            if e.code == 50013: # Missing Permissions
                content = fallback_text or embed.description or "Action Successful."
                header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
                footer = "\n*Note: Enable 'Embed Links' for rich telemetry.*"
                await ctx.send(f"{header}```fix\n{content}\n``` {footer}", ephemeral=ephemeral)
            else:
                raise e

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    @commands.hybrid_command(name="aura", description="Analyze a user's distinct spectral presence.")
    async def aura(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            # Billion-Dollar Algorithmic Seed
            joined_ts = int(target.joined_at.timestamp()) if target.joined_at else 1
            seed = target.id * joined_ts
            rng = random.Random(seed)
            
            hex_code = f"#{rng.randint(0, 0xFFFFFF):06x}".upper()
            resonance = int((trust * 10) + rng.randint(-5, 5))
            resonance = max(0, min(100, resonance))
            
            purity = rng.randint(40, 99)
            if trust < 2.0: purity = rng.randint(5, 30)
            
            # Cutesy Hyacine Aesthetic
            embed = discord.Embed(
                title=f"✧ 𝒜𝓊𝓇𝒶 𝒮𝓅ℯ𝒸𝓉𝓇𝒶𝓁 𝒮𝒾ℊ𝓃𝒶𝓉𝓊𝓇ℯ", 
                color=0xB19CD9 # Hyacine Lavender
            )
            embed.set_author(name=f"{ctx.author.display_name} | {target.display_name}", icon_url=ctx.author.display_avatar.url)
            embed.set_thumbnail(url=target.display_avatar.url)
            
            details = (
                f"**» Spectral Resonance**\n"
                f"Sync Hex: `{hex_code}`\n"
                f"Frequency: **{resonance}%**\n"
                f"Aether Purity: **{purity}%**\n\n"
                f"**» Entity Profile**\n"
                f"Presence: **{'Radiant' if resonance > 70 else 'Stable'}**\n"
                f"Trace: **{'Ancient Lore' if purity > 85 else 'Organic Flow'}**\n\n"
                f"*Quantum footprint verified by Hyacine Protocol.*"
            )
            embed.description = details
            embed.set_footer(text="© Hyacine Lore Engine | Metaphysical Data Map", icon_url=self.bot.user.display_avatar.url)
            await self._send_embed(ctx, embed, fallback_text=f"𝒜𝓊𝓇𝒶 Resonance: **{resonance}%** | Sig: {hex_code}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒜𝓊𝓇𝒶 𝓈𝓎𝓃ℴ𝒽𝓇ℴ𝓃𝒾𝓏𝒶𝓉𝒾ℴ𝓃 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="chronicle", description="Generates a micro-story about recent channel events.")
    @commands.has_permissions(manage_messages=True)
    async def chronicle(self, ctx: commands.Context):
        await ctx.defer()
        try:
            messages = [m async for m in ctx.channel.history(limit=100)]
            if not messages:
                return await ctx.send("⌬ ⟡ **𝒯𝒽ℯ 𝒶𝓇𝒸𝒽𝒾𝓋ℯ𝓈 ℴ𝒻 𝓉𝒽𝒾𝓈 𝓈ℯ𝒸𝓉ℴ𝓇 𝒶𝓇ℯ ℯ𝓃𝓉𝒾𝓇ℯ𝓁𝓎 ℯℳ𝓅𝓉𝓎.**")
                
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
                title=f"❂ 𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ: #{ctx.channel.name}",
                description=f"*{theme}*\n\n{involvement}",
                color=0x2E4053
            )
            embed.set_footer(text="Engine: Hyacine Lore Cartographer")
            await self._send_embed(ctx, embed, fallback_text=f"𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ of #{ctx.channel.name} Analysis Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒞𝒽𝓇ℴ𝓃𝒾𝒸𝓁ℯ 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

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
            title="❈ 𝒲𝒶𝓇ℊ𝒶𝓂ℯ: 𝒯𝒶𝒸𝓉𝒾𝒸𝒶𝓁 𝒮𝒾𝓂𝓊𝓁𝒶𝓉𝒾ℴ𝓃",
            description=f"**Scenario:** {chosen[0]}\n\n**Projection:**\n{chosen[1]}",
            color=0xE74C3C
        )
        embed.set_footer(text="Engine: Hyacine Tactical Predictor")
        await self._send_embed(ctx, embed, fallback_text=f"𝒲𝒶𝓇ℊ𝒶𝓂ℯ Projection Active.")

    @commands.hybrid_command(name="dossier", description="Constructs a fictionalized historical timeline for a user.")
    async def dossier(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            joined = target.joined_at
            if not joined:
                return await ctx.send("⌬ ⟡ **𝒯ℯ𝓂𝓅ℴ𝓇𝒶𝓁 𝒹𝒶𝓉𝒶 𝓂𝒾𝓈𝓈𝒾𝓃𝑔 𝒻ℴ𝓇 𝓉𝒽𝒾𝓈 𝓉𝒶𝓇𝑔ℯ𝓉.**")
                
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
                title=f"𖦹 𝒟ℴ𝓈𝓈𝒾ℯ𝓇: {target.display_name}",
                description="Historical Timeline Reconstruction",
                color=0x34495E
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            
            embed.add_field(name="[ Phase 1: Infiltration ]", value=f"_{entry_phase}_", inline=False)
            embed.add_field(name="[ Phase 2: Integration ]", value=f"_{mid_phase}_", inline=False)
            embed.add_field(name="[ Phase 3: Current State ]", value=f"_{end_phase}_", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Historical Architect")
            await self._send_embed(ctx, embed, fallback_text=f"𝒟ℴ𝓈𝓈𝒾ℯ𝓇 of {target.display_name} Reconstruction Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒟ℴ𝓈𝓈𝒾ℯ𝓇 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="psychoanalyze", description="Extract a target's intentionality matrix.")
    async def psychoanalyze(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            rng = random.Random(target.id + int(time.time() / 3600))
            
            mtrx = ["Subversive", "Protective", "Chaotic", "Algorithmic", "Empathetic"]
            m_val = rng.choice(mtrx)
            
            embed = discord.Embed(
                title=f"❂ 𝒫𝓈𝓎𝒸𝒽ℴ𝓁ℴℊ𝒾𝒸𝒶𝓁 ℳ𝒶𝓉𝓇𝒾𝓍",
                color=0xB19CD9 # Hyacine Lavender
            )
            embed.set_author(name=f"{ctx.author.display_name} | {target.display_name}", icon_url=ctx.author.display_avatar.url)
            embed.set_thumbnail(url=target.display_avatar.url)
            
            details = (
                f"**» Intentionality Scan**\n"
                f"Core Matrix: **{m_val}**\n"
                f"Residue: **{'None' if rng.random() > 0.3 else 'Volatile'}**\n\n"
                f"**» Forecast**\n"
                f"Next Move: `{'Stabilize' if rng.random() > 0.5 else 'Infiltrate'}`\n\n"
                f"*𝒞𝒶𝓊𝓉𝒾ℴℐ: 𝒫𝓈𝓎𝒸𝒽ℴ𝓁ℴ𝑔𝒾𝒸𝒶𝓁 𝓉𝓇𝒶𝒸ℯ 𝒹ℯ𝓉ℯ𝒸𝓉ℯ𝒹.*"
            )
            embed.description = details
            embed.set_footer(text="© Hyacine Lore Engine | Cognitive Archetype Analysis", icon_url=self.bot.user.display_avatar.url)
            await self._send_embed(ctx, embed, fallback_text=f"𝒫𝓈𝓎𝒸𝒽ℴ𝓁ℴ𝓁ℴ𝑔𝒾𝒸𝒶𝓁 Matrix: Core = {m_val}")
        except Exception as e:
             await ctx.send(f"⌬ ⟡ **𝒫𝓈𝓎𝒸𝒽ℴ𝒶𝓃𝒶𝓁𝓎𝓈𝒾𝓈 𝒹𝒾𝓈𝓇𝓊𝓅𝓉ℯ𝒹:** {e}")

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
            title="𖦹 𝒪𝓇𝒶𝒸𝓁ℯ'𝓈 𝒪ℳℯ𝓃",
            description=f"**Prediction:**\n{random.choice(events)}\n\n**ETA:** *{random.choice(timers)}*",
            color=0x9B59B6
        )
        embed.set_footer(text="Engine: Hyacine Prescience Array")
        await self._send_embed(ctx, embed, fallback_text=f"𝒪𝓇𝒶𝒸𝓁ℯ'𝓈 𝒪ℳℯ𝓃 Predicted for this sector.")

async def setup(bot):
    if "LoreEngine" not in bot.cogs:
        await bot.add_cog(LoreEngine(bot))

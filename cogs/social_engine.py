import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone
from redis_utils import rget_json, rset_json
import hashlib

class SocialEngine(commands.Cog):
    """
    Tier 5 & 6: Tension, Gameplay, and Psychological Mechanics.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

    @commands.hybrid_command(name="judgement", description="Hyacine evaluates a user dramatically.")
    async def judgement(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(user.id), 5.0)
            
            # Algorithmic seed based on daily timestamp and user ID
            seed = str(user.id) + datetime.datetime.now(timezone.utc).strftime("%Y%m%d")
            rng = random.Random(seed)
            
            if trust > 7:
                verdict = "Loyal"
                threat = "Negligible"
                dispo = "Acceptable"
                rec = "Grant tactical independence"
                color = 0x2ECC71
            elif trust > 4:
                verdict = "Expendable"
                threat = "Low"
                dispo = "Unpredictable"
                rec = "Keep under observation"
                color = 0xF1C40F
                
                if rng.random() > 0.5:
                    verdict = "Ambitious"
                    dispo = "Suspiciously quiet"
            else:
                verdict = "Traitorous"
                threat = "Severe"
                dispo = "Hostile"
                rec = "Prepare containment protocols"
                color = 0xE74C3C
                
            embed = discord.Embed(
                title=f"⚖️ Judgement: {user.display_name}",
                color=color
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            embed.add_field(name="Verdict", value=f"**{verdict}**", inline=True)
            embed.add_field(name="Threat Level", value=f"**{threat}**", inline=True)
            embed.add_field(name="Disposition", value=f"**{dispo}**", inline=True)
            embed.add_field(name="Recommendation", value=f"*{rec}*", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Psychological Profiler")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Judgement clouded: {e}")

    @commands.hybrid_command(name="fealty", description="Measures allegiance to the server.")
    async def fealty(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            days_active = (datetime.datetime.now(timezone.utc) - target.joined_at).days if target.joined_at else 1
            
            idx = min(100, int((trust / 10) * 80 + min(20, days_active)))
            
            if idx > 90:
                align = "Inner Circle"
                betrayal = "None"
            elif idx > 60:
                align = "Vanguard Force"
                betrayal = "Minimal"
            elif idx > 30:
                align = "Mercenary"
                betrayal = "Moderate"
            else:
                align = "Infiltrator"
                betrayal = "Immediate"
                
            embed = discord.Embed(title=f"⚔️ Fealty Index: {target.display_name}", color=0x34495E)
            embed.add_field(name="Loyalty Index", value=f"**{idx}%**", inline=True)
            embed.add_field(name="Alignment", value=f"**{align}**", inline=True)
            embed.add_field(name="Risk of Betrayal", value=f"**{betrayal}**", inline=False)
            
            embed.set_footer(text="Engine: Hyacine Allegiance Tracking")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Fealty extraction failed: {e}")

    @commands.hybrid_command(name="vendetta", description="Creates a temporary 2-hour rivalry lock.")
    async def vendetta(self, ctx: commands.Context, target: discord.Member):
        await ctx.defer()
        try:
            if target.id == ctx.author.id:
                return await ctx.send("You cannot declare a vendetta against yourself.")
                
            key = f"vendetta:{ctx.guild.id}:{ctx.author.id}:{target.id}"
            active = await self._safe_rget(key)
            
            if active.get("active"):
                return await ctx.send("A vendetta is already active between you two. Resolve it by accumulating messages.")
                
            await self._safe_rset(key, {
                "active": True,
                "expires": (datetime.datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
                "u1": ctx.author.id,
                "u2": target.id,
                "target_msgs": 25
            })
            
            embed = discord.Embed(
                title="🩸 Vendetta Declared",
                description=f"{ctx.author.mention} has challenged {target.mention} to a rivalry.",
                color=0xE74C3C
            )
            embed.add_field(name="Objective", value="First to send **25** organic messages wins influence.", inline=False)
            embed.add_field(name="Time Limit", value="2 Hours", inline=False)
            embed.set_footer(text="Engine: Hyacine Social Tension Matrix")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Declaration failed: {e}")

    @commands.hybrid_command(name="clash", description="Quick skill duel mechanic.")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def clash(self, ctx: commands.Context, opponent: discord.Member):
        if opponent.bot or opponent.id == ctx.author.id:
            return await ctx.send("Invalid opponent.", ephemeral=True)
            
        await ctx.send(f"⚔️ {opponent.mention}, **{ctx.author.display_name}** challenges you to a clash!\nType `defend` in the next 15 seconds to accept.")
        
        def check(m):
            return m.author == opponent and m.channel == ctx.channel and m.content.lower() == "defend"
            
        try:
            await self.bot.wait_for('message', timeout=15.0, check=check)
        except:
            return await ctx.send("The opponent fled the clash.")
            
        words = ["execution", "ice", "frost", "shatter", "imperial", "empire", "absolute"]
        word = random.choice(words)
        
        await ctx.send(f"🔥 The clash begins! First to type the reaction word wins.\n\nType: **`{word}`**")
        
        def clash_check(m):
            return m.author in [ctx.author, opponent] and m.channel == ctx.channel and m.content.lower() == word
            
        try:
            winner_msg = await self.bot.wait_for('message', timeout=10.0, check=clash_check)
            winner = winner_msg.author
            loser = opponent if winner == ctx.author else ctx.author
            embed = discord.Embed(
                title="☠️ Clash Concluded",
                description=f"**{winner.mention}** struck first and won the clash!\n{loser.display_name} was defeated.",
                color=0x2ECC71
            )
            embed.set_footer(text="Engine: Hyacine Combat Simulator")
            await ctx.send(embed=embed)
        except:
            await ctx.send("Neither side struck in time. The clash results in a draw.")

    @commands.hybrid_command(name="subvert", description="Harmless chaos interaction (Sabotage).")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def subvert(self, ctx: commands.Context, target: discord.Member):
        await ctx.defer()
        if target.bot: return await ctx.send("Machines cannot be subverted.")
        
        val = random.random()
        embed = discord.Embed(title="🕵️ Subversion Attempted", color=0x9B59B6)
        
        if val > 0.7:
            embed.description = f"Outcome: **Success**\nYou successfully undermined {target.mention}'s reputation. Their standing wavers."
            embed.color = 0x2ECC71
        elif val > 0.3:
            embed.description = f"Outcome: **Failed**\nYour sabotage was ineffective, but you vanished before being caught."
            embed.color = 0xF1C40F
        else:
            embed.description = f"Outcome: **Countermeasure Triggered**\n{target.mention} anticipated your move. You exposed yourself instead."
            embed.color = 0xE74C3C
            
        embed.set_footer(text="Engine: Hyacine Subterfuge Logic")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="aegis", description="Declares a protection pact.")
    async def aegis(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        if user.id == ctx.author.id: return await ctx.send("You cannot protect yourself.")
        
        key = f"aegis:{ctx.guild.id}:{ctx.author.id}:{user.id}"
        await self._safe_rset(key, {"active": True, "created": datetime.datetime.now(timezone.utc).isoformat()})
        
        embed = discord.Embed(
            title="🛡️ Aegis Link Established",
            description=f"{ctx.author.mention} has sworn to protect {user.mention}.",
            color=0x3498DB
        )
        embed.add_field(name="Contract", value="If the protected user is penalized, you will share 25% of their penalty weight.", inline=False)
        embed.set_footer(text="Engine: Hyacine Alliance Protocol")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="surveillance", description="Adds someone to Hyacine surveillance.")
    @commands.has_permissions(manage_messages=True)
    async def surveillance(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        embed = discord.Embed(
            title="👁️ Target Locked",
            description=f"**{user.display_name}** has been added to Hyacine's high-priority Watchlist.\n\n*Monitoring escalation patterns...*\n*Behavioral tracking engaged.*",
            color=0xE74C3C
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Engine: Hyacine Omniscience DAEMON")
        await ctx.send(embed=embed)

async def setup(bot):
    if "SocialEngine" not in bot.cogs:
        await bot.add_cog(SocialEngine(bot))

import discord
from discord.ext import commands
import json
import datetime
from datetime import timezone, timedelta
from typing import Optional
from redis_utils import rget_json, rset_json

class PrestigeEngine(commands.Cog):
    """
    Tier 4: Long-Term Hierarchical Progression and Lore.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

    @commands.hybrid_command(name="bestow", description="Hyacine grants a dynamic prestige title to a user.")
    @commands.has_permissions(manage_roles=True)
    async def bestow(self, ctx: commands.Context, user: discord.Member, *, title: str):
        await ctx.defer()
        try:
            key = f"titles:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            user_titles = data.get(str(user.id), [])
            if title not in user_titles:
                user_titles.append(title)
                
            data[str(user.id)] = user_titles
            await self._safe_rset(key, data)
            
            embed = discord.Embed(
                title="🎖️ Prestige Bestowed",
                description=f"By sovereign decree, {user.mention} is now recognized as:\n\n**{title.upper()}**",
                color=0xF1C40F
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Hierarchy Ledger")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Bestowal failed: {e}")

    @commands.hybrid_command(name="canonize", description="Permanently elevates a user to the Server Pantheon.")
    @commands.has_permissions(administrator=True)
    async def canonize(self, ctx: commands.Context, user: discord.Member, *, legacy: str):
        await ctx.defer()
        try:
            key = f"pantheon:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            pantheon = data.get("legends", {})
            pantheon[str(user.id)] = {
                "name": user.display_name,
                "legacy": legacy,
                "date": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
            data["legends"] = pantheon
            await self._safe_rset(key, data)
            
            embed = discord.Embed(
                title="🏛️ Legend Canonized",
                description=f"Archive Entry Created.\n{user.mention} has been immortalized in the Pantheon.",
                color=0x9B59B6
            )
            embed.add_field(name="Eternal Legacy", value=f"*{legacy}*")
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Archival Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Canonization failed: {e}")

    @commands.hybrid_command(name="pantheon", description="Displays the server's absolute elite legends.")
    async def pantheon(self, ctx: commands.Context):
        await ctx.defer()
        try:
            key = f"pantheon:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            legends = data.get("legends", {})
            if not legends:
                return await ctx.send("The Pantheon remains empty. No legends have been canonized.")
                
            embed = discord.Embed(title="🏛️ Hall of Influence", color=0x8E44AD)
            for uid, info in legends.items():
                embed.add_field(
                    name=f"✧ {info['name']}",
                    value=f"_{info['legacy']}_\n└ Canonized: `{info['date']}`",
                    inline=False
                )
            embed.set_footer(text="Engine: Hyacine Archival Core")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Retrieval failed: {e}")

    @commands.hybrid_command(name="bloodline", description="Forge a permanent multi-user faction.")
    @commands.has_permissions(manage_roles=True)
    async def bloodline(self, ctx: commands.Context, name: str, member1: discord.Member, member2: discord.Member, member3: Optional[discord.Member] = None):
        await ctx.defer()
        try:
            key = f"bloodline:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            members = [member1.id, member2.id]
            if member3: members.append(member3.id)
            
            data[name.upper()] = members
            await self._safe_rset(key, data)
            
            mentions = " ".join([f"<@{m}>" for m in members])
            
            embed = discord.Embed(
                title="🩸 Syndicate Formed",
                description=f"A new bloodline has been carved into the server hierarchy.\n\n**Syndicate: {name.upper()}**\nMembers: {mentions}",
                color=0xE74C3C
            )
            embed.set_footer(text="Engine: Hyacine Alliance Matrix")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Syndicate formation failed: {e}")

    @commands.hybrid_command(name="renown", description="Passive algorithmic prestige standing.")
    async def renown(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            
            base_trust = trust_scores.get(str(target.id), 5.0)
            bonus = (datetime.datetime.now(timezone.utc) - target.joined_at).days if target.joined_at else 0
            
            renown_score = int((base_trust * 10) + (bonus * 0.1))
            
            if renown_score > 200: standing = "Apex Operator"
            elif renown_score > 100: standing = "Trusted Lieutenant"
            elif renown_score > 50: standing = "Recognized Asset"
            else: standing = "Unknown Entity"
            
            embed = discord.Embed(title=f"🎖️ Renown Abstract: {target.display_name}", color=0x34495E)
            embed.add_field(name="Aggregate Renown", value=f"**{renown_score}**", inline=True)
            embed.add_field(name="Standing", value=f"**{standing}**", inline=True)
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Prestige Layer")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Renown check failed: {e}")

    @commands.hybrid_command(name="stratum", description="Displays your current hierarchical class.")
    async def stratum(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(ctx.author.id), 5.0)
            
            title_key = f"titles:{ctx.guild.id}"
            titles_data = await self._safe_rget(title_key)
            my_titles = titles_data.get(str(ctx.author.id), [])
            
            tier = "Initiate"
            next_tier = "Vanguard"
            prog = int((trust / 4.0) * 100)
            
            if trust >= 4.0:
                tier = "Vanguard"
                next_tier = "Inner Circle"
                prog = int(((trust - 4.0) / 4.0) * 100)
            if trust >= 8.0:
                tier = "Inner Circle"
                next_tier = "Supreme Commander"
                prog = int(((trust - 8.0) / 2.0) * 100)
                
            embed = discord.Embed(title="🛡️ Biological Stratum", color=0x2C3E50)
            embed.add_field(name="Current Tier", value=f"**{tier}**", inline=True)
            embed.add_field(name="Next Evolution", value=f"**{next_tier}**", inline=True)
            
            prog_bar = "█" * int(prog / 10) + "░" * (10 - int(prog / 10))
            embed.add_field(name="Evolution Progress", value=f"`[{prog_bar}] {prog}%`\n*Ascension requires increased server Trust.*", inline=False)
            
            if my_titles:
                embed.add_field(name="Bestowed Titles", value="\n".join([f"✧ {t}" for t in my_titles]), inline=False)
                
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Evolutionary Matrix")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ | Stratum analysis failed: {e}")

    @commands.hybrid_command(name="awaken", description="Triggers a tier evolution if requirements are met.")
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def awaken(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(ctx.author.id), 5.0)
            
            key = f"awaken:{ctx.guild.id}:{ctx.author.id}"
            last = await self._safe_rget(key)
            if last and trust < 8.0:
                self.awaken.reset_cooldown(ctx)
                return await ctx.send("Your biological stratum is not yet ready for ascension. Increase your server value.")
                
            await self._safe_rset(key, {"timestamp": datetime.datetime.now(timezone.utc).isoformat()})
            
            embed = discord.Embed(
                title="✨ Ascension Triggered",
                description=f"**{ctx.author.display_name}** has broken their limiter.\n\nEvolution Complete: **Aura Cap Increased.**",
                color=0x2ECC71
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Evolutionary Matrix")
            await ctx.send(embed=embed)
        except Exception as e:
            self.awaken.reset_cooldown(ctx)
            await ctx.send(f"❌ | Ascension failed: {e}")

async def setup(bot):
    if "PrestigeEngine" not in bot.cogs:
        await bot.add_cog(PrestigeEngine(bot))

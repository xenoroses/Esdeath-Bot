import discord
from discord.ext import commands
import json
import datetime
from datetime import datetime, timezone, timedelta
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

    async def _check_hierarchy(self, ctx, member):
        """Unified rank check to prevent raw Forbidden errors."""
        if not isinstance(member, discord.Member): return True
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("⌬ ⟡ **𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ𝒩ℐℰ𝒟:** Subject ranks equal to or above your authority.", ephemeral=True)
            return False
        if member.id == ctx.guild.owner_id:
            await ctx.send("⌬ ⟡ **𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴:** Owner cannot be processed.", ephemeral=True)
            return False
        if member.top_role >= ctx.me.top_role:
            await ctx.send("⌬ ⟡ **𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟:** Target's rank exceeds my system permissions.", ephemeral=True)
            return False
        return True

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
                title="✵ 𝒫𝓇ℯ𝓈𝓉𝒾ℊℯ ℬℯ𝓈𝓉ℴ𝓌ℯ𝒹",
                description=f"By sovereign decree, {user.mention} is now recognized as:\n\n**{title.upper()}**",
                color=0xF1C40F
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            if not await self._check_hierarchy(ctx, user): return
            embed.set_footer(text="Engine: Hyacine Hierarchy Ledger")
            await self._send_embed(ctx, embed, fallback_text=f"𝒫𝓇ℯ𝓈𝓉𝒾ℊℯ Bestowed: {user.mention} is now known as **{title}**")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℬℯ𝓈𝓉ℴ𝓌𝒶𝓁 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

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
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
            data["legends"] = pantheon
            await self._safe_rset(key, data)
            
            embed = discord.Embed(
                title="❂ ℒℯℊℯ𝓃𝒹 𝒞𝒶𝓃ℴ𝓃𝒾𝓏ℯ𝒹",
                description=f"Archive Entry Created.\n{user.mention} has been immortalized in the Pantheon.",
                color=0x9B59B6
            )
            embed.add_field(name="Eternal Legacy", value=f"*{legacy}*")
            embed.set_thumbnail(url=user.display_avatar.url)
            if not await self._check_hierarchy(ctx, user): return
            embed.set_footer(text="Engine: Hyacine Archival Core")
            await self._send_embed(ctx, embed, fallback_text=f"ℒℯℊℯ𝓃𝒹 Canonized: {user.mention} immortalized.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒞𝒶𝓃ℴ𝓃𝒾𝓏𝒶𝓉𝒾ℴ𝓃 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="pantheon", description="Displays the server's absolute elite legends.")
    async def pantheon(self, ctx: commands.Context):
        await ctx.defer()
        try:
            key = f"pantheon:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            legends = data.get("legends", {})
            if not legends:
                return await ctx.send("⌬ ⟡ **𝒯𝒽ℯ 𝒫𝒶𝓃ℴ𝒽ℯℴ𝓃 𝓇ℯ𝓂𝒶𝒾𝓃𝓈 ℯ𝓂𝓅𝓉𝓎. 𝒩ℴ 𝓁ℯ𝑔ℯ𝓃𝒹𝓈 𝒽𝒶𝓋ℯ 𝒷ℯℯ𝓃 𝒸𝒶𝓃ℴ𝓃𝒾𝓏ℯ𝒹.**")
                
            embed = discord.Embed(title="❂ ℋ𝒶𝓁𝓁 ℴ𝒻 ℐℳ𝓁𝓊ℯ𝓃𝒸ℯ", color=0x8E44AD)
            # SCALE GUARD: Limit to top 20 legends to prevent overflow
            for uid, info in list(legends.items())[:20]:
                embed.add_field(
                    name=f"✧ {info['name']}",
                    value=f"_{info['legacy']}_\n└ Canonized: `{info['date']}`",
                    inline=False
                )
            embed.set_footer(text="Engine: Hyacine Archival Core")
            await self._send_embed(ctx, embed, fallback_text=f"𝒫𝒶𝓃𝓉ℯ𝓁𝓁 of Influence Retrieval Complete.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℛℯ𝓉𝓇𝒾ℯ𝓋𝒶𝓁 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="bloodline", description="Forge a permanent multi-user faction.")
    @commands.has_permissions(manage_roles=True)
    async def bloodline(self, ctx: commands.Context, name: str, member1: discord.Member, member2: discord.Member, member3: Optional[discord.Member] = None):
        await ctx.defer()
        try:
            key = f"bloodline:{ctx.guild.id}"
            data = await self._safe_rget(key)
            
            members = [member1.id, member2.id]
            if member3: members.append(member3.id)
            
            if not await self._check_hierarchy(ctx, member1) or not await self._check_hierarchy(ctx, member2): return
            if member3 and not await self._check_hierarchy(ctx, member3): return
            data[name.upper()] = members
            await self._safe_rset(key, data)
            
            mentions = " ".join([f"<@{m}>" for m in members])
            
            embed = discord.Embed(
                title="❈ 𝒮𝓎𝓃𝒹𝒾𝒸𝒶𝓉ℯ ℱℴℛ𝓂ℯ𝒹",
                description=f"A new bloodline has been carved into the server hierarchy.\n\n**Syndicate: {name.upper()}**\nMembers: {mentions}",
                color=0xE74C3C
            )
            embed.set_footer(text="Engine: Hyacine Alliance Matrix")
            await self._send_embed(ctx, embed, fallback_text=f"𝒮𝓎𝓃𝒹𝒾𝒸𝒶𝓉ℯ {name.upper()} Formed with {len(members)} assets.")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓎𝓃𝒹𝒾𝒸𝒶𝓉ℯ 𝒻ℴ𝓇𝓂𝒶𝓉𝒾ℴ𝓃 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="renown", description="Passive algorithmic prestige standing.")
    async def renown(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            trust_scores = await self._safe_rget("trust_scores")
            
            base_trust = trust_scores.get(str(target.id), 5.0)
            now = datetime.now(timezone.utc)
            bonus = (now - target.joined_at.replace(tzinfo=timezone.utc)).days if target.joined_at else 0
            
            renown_score = int((base_trust * 10) + (bonus * 0.1))
            
            if renown_score > 200: standing = "Apex Operator"
            elif renown_score > 100: standing = "Trusted Lieutenant"
            elif renown_score > 50: standing = "Recognized Asset"
            else: standing = "Unknown Entity"
            
            embed = discord.Embed(title=f"✵ ℛℯ𝓃ℴ𝓌𝓃 𝒜𝒷𝓈𝓉𝓇𝒶𝒸𝓉: {target.display_name}", color=0x34495E)
            embed.add_field(name="Aggregate ℛℯ𝓃ℴ𝓌𝓃", value=f"**{renown_score}**", inline=True)
            embed.add_field(name="Standing", value=f"**{standing}**", inline=True)
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Prestige Layer")
            await self._send_embed(ctx, embed, fallback_text=f"ℛℯ𝓃ℴ𝓌𝓃 Score: **{renown_score}** | Standing: {standing}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℛℯ𝓃ℴ𝓌𝓃 𝒸𝒽ℯ𝒸𝓀 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

    @commands.hybrid_command(name="stratum", description="Displays your current hierarchical evolution.")
    async def stratum(self, ctx: commands.Context):
        await ctx.defer()
        try:
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(ctx.author.id), 5.0)
            
            p_key = f"prestige:{ctx.author.id}"
            p_data = await self._safe_rget(p_key)
            points = p_data.get("points", 0)
            
            # Dynamic Tiering (HSR Style)
            if trust >= 9.0:
                tier = "Aeon Emissary"
                next_tier = "Ultima"
                prog = min(100, int((trust - 9.0) / 1.0 * 100))
                color = 0xF1C40F
            elif trust >= 7.0:
                tier = "Stellar Vanguard"
                next_tier = "Aeon Emissary"
                prog = int((trust - 7.0) / 2.0 * 100)
                color = 0x9B59B6
            elif trust >= 4.0:
                tier = "Pathstrider"
                next_tier = "Stellar Vanguard"
                prog = int((trust - 4.0) / 3.0 * 100)
                color = 0x3498DB
            else:
                tier = "Mortal Follower"
                next_tier = "Pathstrider"
                prog = int((trust / 4.0) * 100)
                color = 0x95A5A6
                
            # Cutesy Hyacine Aesthetic
            embed = discord.Embed(
                title=f"⟡ ℬ𝒾ℴ𝓁ℴ𝑔𝒾𝒸𝒶𝓁 𝒮𝓉𝓇𝒶ℯ𝓁𝓁𝓊𝓂: {ctx.author.display_name}", 
                color=0xB19CD9 # Hyacine Lavender
            )
            embed.set_author(name="Stellar Evolution Archive", icon_url=ctx.author.display_avatar.url)
            
            # Cutesy Progress Bar
            prog_bar = "🌸" * int(prog / 10) + "✨" * (10 - int(prog / 10))
            
            details = (
                f"**» Current Evolution**\n"
                f"Tier: **{tier}**\n"
                f"Sync Points: **{points}**\n"
                f"Trust Index: **{trust:.2f}**\n\n"
                f"**» Path of Ascension**\n"
                f"Next Goal: **{next_tier}**\n"
                f"Progress: `[{prog_bar}]` **{prog}%**\n\n"
                f"*Protocol: Stellar Synergy reached. ⟡*"
            )
            embed.description = details
            embed.set_footer(text="© Hyacine Protocol | Evolutionary Data Map", icon_url=self.bot.user.display_avatar.url)
            await self._send_embed(ctx, embed, fallback_text=f"ℬ𝒾ℴ𝓁ℴ𝑔𝒾𝒸𝒶𝓁 𝒮𝓉𝓇𝒶𝓉𝓊𝓂: Tier = {tier} | Sync = {points}")
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **𝒮𝓉𝓇𝒶𝓉𝓊𝓂 𝒶𝓃𝒶𝓁𝓎𝓈𝒾𝓈 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

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
                return await ctx.send("⌬ ⟡ **𝒴ℴ𝓊𝓇 𝒷𝒾ℴ𝓁ℴ𝑔𝒾𝒸𝒶𝓁 𝓈𝓉ℯ𝓁𝓁𝒶𝓇 𝓈𝓉𝓇𝒶𝓉𝓊𝓂 𝒾𝓈 𝓃ℴ𝓉 𝓎ℯ𝓉 𝓇ℯ𝒶𝒹𝓎 𝒻ℴ𝓇 𝒶𝓈𝒸ℯ𝓃𝓈𝒾ℴ𝓃.**")
                
            await self._safe_rset(key, {"timestamp": datetime.now(timezone.utc).isoformat()})
            
            embed = discord.Embed(
                title="✧ 𝒜𝓈𝒸ℯ𝓃𝓈𝒾ℴ𝓃 𝒯𝓇𝒾ℊℊℯ𝓇ℯ𝒹",
                description=f"**{ctx.author.display_name}** has broken their limiter.\n\nEvolution Complete: **Aura Cap Increased.**",
                color=0x2ECC71
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Engine: Hyacine Evolutionary Matrix")
            await self._send_embed(ctx, embed, fallback_text=f"𝒜𝓈𝒸ℯ𝓃𝓈𝒾ℴ𝓃 Triggered: Evolution Complete.")
        except Exception as e:
            self.awaken.reset_cooldown(ctx)
            await ctx.send(f"⌬ ⟡ **𝒜𝓈𝒸ℯ𝓃𝓈𝒾ℴ𝓃 𝒻𝒶𝒾𝓁ℯ𝒹:** {e}")

async def setup(bot):
    if "PrestigeEngine" not in bot.cogs:
        await bot.add_cog(PrestigeEngine(bot))

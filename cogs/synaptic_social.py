import discord
from discord.ext import commands
import random
import datetime
from datetime import timezone
from redis_utils import rget_json, rset_json, rget, rset
import json

class SynapticSocial(commands.Cog):
    """
    Tier 7: The Synaptic Identity Layer - Billion-Dollar Social Engineering.
    Refactored into Groups to stay under the 100 slash-command limit.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _safe_rget(self, key):
        return await rget_json(self.bot, key) or {}

    async def _safe_rset(self, key, val):
        await rset_json(self.bot, key, val)

    # --- SYNAPSE MASTER GROUP ---
    @commands.hybrid_group(name="synapse", description="Access the Synaptic Identity Layer.", invoke_without_command=True)
    async def synapse_group(self, ctx: commands.Context):
        """Default: Show usage."""
        await ctx.send_help(ctx.command)

    @synapse_group.command(name="essence", description="View a user's unified social identity profile.")
    async def essence(self, ctx: commands.Context, user: discord.Member = None):
        await ctx.defer()
        try:
            target = user or ctx.author
            bonds = await self._safe_rget(f"social:bonds:{ctx.guild.id}")
            bond_target_id = bonds.get(str(target.id))
            bond_user = ctx.guild.get_member(int(bond_target_id)) if bond_target_id else None
            
            # Standardized Set Gaze Member fetch
            obs_count = 0
            if self.bot.redis:
                observers = await self.bot.redis.smembers(f"social:gaze:{target.id}")
                obs_count = len(observers) if observers else 0
            
            signs = await self._safe_rget(f"social:signs:{target.id}")
            sign_count = len(signs) if isinstance(signs, list) else 0
            trust_scores = await self._safe_rget("trust_scores")
            trust = trust_scores.get(str(target.id), 5.0)
            
            # Binary Flag check
            is_eclipsed = await rget(self.bot, f"social:eclipse:{target.id}") == "true"
            mystery_rank = "High ❂" if is_eclipsed else ("Standard ⌬" if obs_count < 5 else "Exposed ✧")

            embed = discord.Embed(title=f"✧ 𝒮𝓎𝓃𝒶𝓅𝓉𝒾𝒸 ℰ𝓈𝓈ℯ𝓃𝒸ℯ: {target.display_name}", color=0xB19CD9)
            embed.set_author(name=f"Identity Layer | Protocol", icon_url=target.display_avatar.url)
            embed.set_thumbnail(url=target.display_avatar.url)
            resonance_str = f"Synced with **{bond_user.mention}**" if bond_user else "Unsynchronized ⌬"
            embed.description = (
                f"**» Core Resonance**\nStatus: {resonance_str}\nTrust Index: **{trust:.2f}**\n\n"
                f"**» Fixation Metrics**\nObservations: **{obs_count}** cycle(s)\nSoul Signs: **{sign_count}** persistent\n"
                f"Mystery Rank: **{mystery_rank}**\n\n*Verified by Hyacine Identity Layer.*"
            )
            embed.set_footer(text="© Hyacine Protocol | Synaptic Intelligence Array")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⌬ ⟡ **ℰ𝓈𝓈ℯ𝓃𝒸ℯ 𝓇ℯ𝓉𝓇𝒾ℯ𝓋𝒶𝓁 𝒹𝒾𝓈𝓇𝓊𝓅𝓉ℯ𝒹:** {e}")

    @synapse_group.command(name="resonance", description="Propose a social resonance bond.")
    async def resonance(self, ctx: commands.Context, target: discord.Member):
        if target.bot or target.id == ctx.author.id: return
        await ctx.send(f"✾ {target.mention}, **{ctx.author.display_name}** requests a Synaptic Resonance Bond. Type `synchronize` in 30s to accept.")
        def check(m): return m.author == target and m.channel == ctx.channel and m.content.lower() == "synchronize"
        try:
            await self.bot.wait_for('message', timeout=30.0, check=check)
            b_key = f"social:bonds:{ctx.guild.id}"
            bonds = await self._safe_rget(b_key)
            bonds[str(ctx.author.id)] = str(target.id)
            bonds[str(target.id)] = str(ctx.author.id)
            await self._safe_rset(b_key, bonds)
            await ctx.send(embed=discord.Embed(title="✧ ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ 𝒮ℴ𝓁𝒾𝒹𝒾𝒻𝒾ℯ𝒹", description=f"Bond established between **{ctx.author.display_name}** and **{target.display_name}**.", color=0xB19CD9))
        except: await ctx.send("⌬ ⟡ **ℛℯ𝓈ℴ𝓃𝒶𝓃𝒸ℯ 𝒻𝒶𝒹ℯ𝒹.**")

    @synapse_group.command(name="gaze", description="Leave a silent, anonymous fixation trace.")
    async def gaze(self, ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id: return
        # Standardize Gaze Set
        gaze_key = f"social:gaze:{target.id}"
        if self.bot.redis:
            await self.bot.redis.sadd(gaze_key, ctx.author.id)
        
        obs_key = f"social:obsess:{target.id}"
        current = int(await rget(self.bot, obs_key) or 0)
        await rset(self.bot, obs_key, str(current + 1))
        await ctx.send("✧ 𝒴ℴ𝓊𝓇 𝑔𝒶𝓏ℯ 𝒽𝒶𝓈 𝒷ℯℯ𝓃 𝒻ℯ𝓁𝓉.", ephemeral=True)

    @synapse_group.command(name="trace", description="View fixation traces on your essence.")
    async def trace(self, ctx: commands.Context):
        gaze_key = f"social:gaze:{ctx.author.id}"
        count = 0
        if self.bot.redis:
            members = await self.bot.redis.smembers(gaze_key)
            count = len(members) if members else 0
            
        total = int(await rget(self.bot, f"social:obsess:{ctx.author.id}") or 0)
        embed = discord.Embed(title="❂ ℱ𝒾𝓍𝒶𝓉iℴ𝓃 𝒯𝓇𝒶𝒸ℯ", description=f"**{count}** entities fixated.\nHistorical cycles: **{total}**", color=0xB19CD9)
        await ctx.send(embed=embed)

    @synapse_group.command(name="mark", description="Leave a persistent, anonymous soul-sign.")
    async def signature(self, ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id: return
        signs = await self._safe_rget(f"social:signs:{target.id}") or []
        signs.append({"from_id": ctx.author.id, "ts": datetime.datetime.now(timezone.utc).isoformat()})
        await self._safe_rset(f"social:signs:{target.id}", signs)
        await ctx.send(f"✧ 𝒮𝓊𝒸𝒸ℯ𝓈𝓈𝒻𝓊𝓁𝓁𝓎 𝓁ℯ𝒻𝓉 𝒶 **𝒮ℴ𝓊𝓁 𝒮𝒾𝑔𝓃𝒶𝓉ℯ𝓊𝓇ℯ**.", ephemeral=True)

    @synapse_group.command(name="veil", description="Mask your essence metadata.")
    async def eclipse(self, ctx: commands.Context):
        state = "true" if not (await rget(self.bot, f"social:eclipse:{ctx.author.id}") == "true") else "false"
        await rset(self.bot, f"social:eclipse:{ctx.author.id}", state)
        await ctx.send(f"⌬ ℰ𝒸𝓁𝒾𝓅𝓈ℯ 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁: {'Engaged ❂' if state == 'true' else 'Deactivated ✧'}")

    @synapse_group.command(name="signal", description="Send a high-tension sensory pulse.")
    async def link(self, ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id: return
        await target.send(f"✾ | **{ctx.author.display_name}** sent a **𝒮ℯ𝓃𝓈ℴ𝓇𝓎 ℒ𝒾𝓃𝓀** from {ctx.guild.name}. Respond with `sync`.")
        await ctx.send(f"✧ 𝒮ℯ𝓃𝓈ℴ𝓇𝓎 𝓈𝒾𝑔𝓃𝒶𝓁 𝓉𝓇𝒶𝓃𝓈𝓂𝒾𝓉𝓉ℯ𝒹.", ephemeral=True)

    @synapse_group.command(name="sync", description="Secret mutual attraction check.")
    async def sync(self, ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id: return
        check_key = f"social:sync:{ctx.guild.id}:{target.id}:{ctx.author.id}"
        check_val = await rget(self.bot, check_key)
        if check_val:
            await ctx.send(embed=discord.Embed(title="Resonance Breach!", description=f"ℳ𝓊𝓉𝓊𝒶𝓁 𝓈y𝓃𝒸𝒽𝓇ℴ𝓃𝒾𝓏𝒶𝓉𝒾ℴ𝓃 between **{ctx.author.mention}** and **{target.mention}**!", color=0xE74C3C))
            if self.bot.redis:
                await self.bot.redis.delete(check_key)
        else:
            save_key = f"social:sync:{ctx.guild.id}:{ctx.author.id}:{target.id}"
            await rset(self.bot, save_key, "active")
            if self.bot.redis:
                await self.bot.redis.expire(save_key, 604800)
            await ctx.send(f"✧ 𝒮𝓎𝓃𝒸𝒽𝓇ℴ𝓃𝒾𝓏𝒶𝓉𝒾ℴ𝓃 𝒶𝓉𝓉ℯ𝓂𝓅𝓉 𝓇ℯ𝒸ℴ𝓇𝒹ℯ𝒹.", ephemeral=True)

    @synapse_group.command(name="meridian", description="Server social temperature scan.")
    async def meridian(self, ctx: commands.Context):
        await ctx.defer()
        # Scale Optimized History
        msgs_count = 0
        mentions = 0
        reactions = 0
        async for m in ctx.channel.history(limit=200):
            msgs_count += 1
            mentions += len(m.mentions)
            reactions += len(m.reactions)
            
        intensity = min(100, int((mentions * 5) + (reactions * 2)))
        temp = "Supernova ❂" if intensity > 80 else ("Solar Flare ✧" if intensity > 50 else "Cold Void ⌬")
        embed = discord.Embed(title="🌡️ 𝒮ℴ𝒸𝒾𝒶𝓁 ℳℯ𝓇𝒾𝒹𝒾𝒶𝓃", description=f"Intensity Pulse: **{intensity}%**\nThermal Phase: **{temp}**", color=0xB19CD9)
        await ctx.send(embed=embed)

    @synapse_group.command(name="void", description="Open a high-security aether loop.")
    @commands.has_permissions(manage_threads=True)
    async def void(self, ctx: commands.Context, partner: discord.Member):
        if partner.id == ctx.author.id or partner.bot: return
        await ctx.defer(ephemeral=True)
        thread = await ctx.channel.create_thread(name=f"Void Loop: {ctx.author.display_name} ⟡ {partner.display_name}", auto_archive_duration=60, type=discord.ChannelType.private_thread)
        await thread.add_user(ctx.author); await thread.add_user(partner)
        await thread.send(embed=discord.Embed(title="⌬ 𝒜ℯ𝓉𝒽ℯ𝓇 𝒱ℴ𝒾𝒹", description=f"Isolated loop established between **{ctx.author.display_name}** and **{partner.display_name}**.", color=0x2B2D31))
        await ctx.send(f"✧ 𝒱ℴ𝒾𝒹 ℒℴℴ𝓅 ℯ𝓈𝓉𝒶𝒷𝓁𝒾𝓈𝒽ℯ𝒹: {thread.jump_url}", ephemeral=True)

    @synapse_group.command(name="pulse", description="Server social velocity scan.")
    async def pulse(self, ctx: commands.Context):
        await ctx.defer()
        tensions = 0
        total = 0
        async for m in ctx.channel.history(limit=400):
            total += 1
            if "!" in m.content or m.mentions:
                tensions += 1
        
        tension_pct = (tensions / max(total, 1)) * 100
        prog = "✧" * int(tension_pct / 10) + "◈" * (10 - int(tension_pct / 10))
        embed = discord.Embed(title="𖦹 𝒢𝓁ℴ𝒷𝒶𝓁 𝒮ℯ𝓃𝓈ℴ𝓇y 𝒫𝓊𝓁𝓈ℯ", description=f"Tension Level: **{tension_pct:.1f}%**\nSync Status: `[{prog}]`", color=0xB19CD9)
        await ctx.send(embed=embed)

async def setup(bot):
    if "SynapticSocial" not in bot.cogs:
        await bot.add_cog(SynapticSocial(bot))

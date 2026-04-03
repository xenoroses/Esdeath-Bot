import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

class EnterpriseTools(commands.Cog):
    """Enterprise-grade moderation tools for large servers."""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def rget(self, key: str) -> str:
        """Redis get helper."""
        return await self.bot.rget(key)
    
    async def rset(self, key: str, value: str):
        """Redis set helper."""
        await self.bot.rset(key, value)
    
    async def rget_json(self, key: str) -> dict:
        """Redis get JSON helper."""
        data = await self.rget(key)
        return json.loads(data) if data else {}
    
    async def rset_json(self, key: str, data: dict):
        """Redis set JSON helper."""
        await self.rset(key, json.dumps(data))
    
    async def _send_error(self, ctx, message: str):
        """Send error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=0xE74C3C
        )
        await ctx.send(embed=embed)
    
    async def _send_success(self, ctx, message: str):
        """Send success embed."""
        embed = discord.Embed(
            title="✅ Success",
            description=message,
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    # --- SHADOW BAN SYSTEM ---
    @commands.hybrid_command(name="shadowban", description="Silently isolate a user from server interactions.")
    @commands.has_permissions(ban_members=True)
    async def shadowban(self, ctx: commands.Context, user: discord.Member, reason: str = "Shadow ban"):
        """
        Shadow ban a user - they can see the server but cannot interact:
        /shadowban @user "reason" - Apply shadow ban
        /shadowban @user - Check shadow ban status
        """
        shadowbans = await self.rget_json("shadowbans") or {}
        user_id = str(user.id)
        
        if user_id in shadowbans:
            # Remove shadow ban
            del shadowbans[user_id]
            await self.rset_json("shadowbans", shadowbans)
            
            # Restore permissions
            for channel in ctx.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(user, overwrite=None)
                    except:
                        continue
            
            await self._send_success(ctx, f"Removed shadow ban from {user.mention}")
        else:
            # Apply shadow ban
            shadowbans[user_id] = {
                "reason": reason,
                "banned_by": ctx.author.id,
                "banned_at": datetime.now(timezone.utc).isoformat(),
                "username": user.display_name
            }
            await self.rset_json("shadowbans", shadowbans)
            
            # Apply restrictions to all channels
            overwrite = discord.PermissionOverwrite(
                send_messages=False,
                add_reactions=False,
                speak=False,
                use_voice_activation=False
            )
            
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(user, overwrite=overwrite)
                except:
                    continue
            
            embed = discord.Embed(
                title="🌑 Shadow Ban Applied",
                description=f"Silently isolated {user.mention}",
                color=0x34495E
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Applied By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Timestamp", value=datetime.now().strftime("%Y-%m-%d %H:%M UTC"), inline=True)
            
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="shadowlist", description="List all shadow banned users.")
    @commands.has_permissions(ban_members=True)
    async def shadowlist(self, ctx: commands.Context):
        """List all users currently shadow banned."""
        shadowbans = await self.rget_json("shadowbans") or {}
        
        if not shadowbans:
            return await ctx.send("🌑 No users are currently shadow banned.")
        
        embed = discord.Embed(
            title="🌑 Shadow Ban List",
            description=f"**{len(shadowbans)}** users currently isolated",
            color=0x34495E
        )
        
        for user_id, data in shadowbans.items():
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = data.get("username", "Unknown")
            
            embed.add_field(
                name=username,
                value=f"Reason: {data['reason']}\nBanned: {data['banned_at'][:10]}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    # --- INVESTIGATION SYSTEM ---
    @commands.hybrid_command(name="investigate", description="Deep investigation of user activity and patterns.")
    @commands.has_permissions(manage_guild=True)
    async def investigate(self, ctx: commands.Context, user: discord.Member, depth: str = "basic"):
        """
        Conduct deep investigation of a user:
        /investigate @user - Basic investigation
        /investigate @user deep - Comprehensive analysis
        """
        await ctx.defer()
        
        try:
            embed = discord.Embed(
                title=f"🔍 Investigation: {user.display_name}",
                description=f"Deep analysis of user activity and patterns",
                color=0xF39C12
            )
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
            # Basic user info
            embed.add_field(
                name="👤 User Information",
                value=f"**ID:** {user.id}\n**Joined:** {user.joined_at.strftime('%Y-%m-%d') if user.joined_at else 'Unknown'}\n**Created:** {user.created_at.strftime('%Y-%m-%d')}\n**Roles:** {len(user.roles)-1}",
                inline=True
            )
            
            if depth == "deep":
                # Message analysis (last 7 days)
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                message_stats = {}
                total_messages = 0
                
                for channel in ctx.guild.text_channels:
                    try:
                        channel_msgs = 0
                        async for message in channel.history(after=cutoff_time, limit=500):
                            if message.author.id == user.id:
                                channel_msgs += 1
                                total_messages += 1
                        
                        if channel_msgs > 0:
                            message_stats[channel.name] = channel_msgs
                    except:
                        continue
                
                # Activity patterns
                embed.add_field(
                    name="📊 Activity Analysis (7d)",
                    value=f"**Total Messages:** {total_messages}\n**Active Channels:** {len(message_stats)}\n**Avg Daily:** {total_messages/7:.1f}",
                    inline=True
                )
                
                # Trust and behavior
                trust_scores = await self.rget_json("trust_scores") or {}
                user_trust = trust_scores.get(str(user.id), 5.0)
                
                embed.add_field(
                    name="🛡️ Trust & Behavior",
                    value=f"**Trust Score:** {user_trust:.1f}/10\n**Shadow Banned:** {'Yes' if str(user.id) in (await self.rget_json('shadowbans') or {}) else 'No'}",
                    inline=True
                )
                
                # Top channels
                if message_stats:
                    top_channels = sorted(message_stats.items(), key=lambda x: x[1], reverse=True)[:3]
                    channels_text = "\n".join([f"#{chan}: {count}" for chan, count in top_channels])
                    embed.add_field(
                        name="📍 Channel Activity",
                        value=channels_text,
                        inline=False
                    )
            
            embed.set_footer(text=f"Investigation by Esdeath | {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._send_error(ctx, f"Investigation failed: {e}")

    # --- SERVER LOCKDOWN ---
    @commands.hybrid_command(name="lockdown", description="Emergency server lockdown controls.")
    @commands.has_permissions(manage_guild=True)
    async def lockdown(self, ctx: commands.Context, action: str, target: str = "all"):
        """
        Emergency server lockdown:
        /lockdown enable - Lock all channels
        /lockdown disable - Unlock all channels
        /lockdown enable #channel - Lock specific channel
        """
        if action not in ["enable", "disable"]:
            return await self._send_error(ctx, "Action must be 'enable' or 'disable'")
        
        await ctx.defer()
        
        try:
            lockdown_role = discord.utils.get(ctx.guild.roles, name="Lockdown")
            if not lockdown_role:
                lockdown_role = await ctx.guild.create_role(
                    name="Lockdown",
                    color=0xE74C3C,
                    reason="Emergency lockdown role"
                )
            
            if target == "all":
                channels = ctx.guild.text_channels
            else:
                # Try to find specific channel
                channel = discord.utils.get(ctx.guild.text_channels, name=target.lstrip("#"))
                if not channel:
                    return await self._send_error(ctx, f"Channel '{target}' not found")
                channels = [channel]
            
            if action == "enable":
                # Apply lockdown
                overwrite = discord.PermissionOverwrite(send_messages=False)
                
                for channel in channels:
                    try:
                        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                        await channel.set_permissions(lockdown_role, overwrite=None)
                    except:
                        continue
                
                embed = discord.Embed(
                    title="🔒 Server Lockdown Activated",
                    description=f"Locked {len(channels)} channel{'s' if len(channels) != 1 else ''}",
                    color=0xE74C3C
                )
                
            else:  # disable
                # Remove lockdown
                for channel in channels:
                    try:
                        await channel.set_permissions(ctx.guild.default_role, overwrite=None)
                    except:
                        continue
                
                embed = discord.Embed(
                    title="🔓 Server Lockdown Deactivated",
                    description=f"Unlocked {len(channels)} channel{'s' if len(channels) != 1 else ''}",
                    color=0x2ECC71
                )
            
            embed.add_field(
                name="Emergency Role",
                value=f"Users with {lockdown_role.mention} can still post",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._send_error(ctx, f"Lockdown {action} failed: {e}")

async def setup(bot):
    await bot.add_cog(EnterpriseTools(bot))
import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime, timezone
from typing import Optional, Union
from redis_utils import rget_json, rset_json, rdelete, rget, rset

class ConfessionModal(discord.ui.Modal, title="Anonymous Confession Portal"):
    def __init__(self, cog: "ConfessionEngine"):
        super().__init__()
        self.cog = cog
        self.confession_input = discord.ui.TextInput(
            label="Your Anonymous Confession",
            style=discord.TextStyle.paragraph,
            placeholder="Type your confession here... Your identity will remain hidden from server members.",
            max_length=2000,
            required=True
        )
        self.add_item(self.confession_input)

    async def on_submit(self, interaction: discord.Interaction):
        confession_text = self.confession_input.value.strip()
        if not confession_text:
            return await interaction.response.send_message("❌ Confession text cannot be empty.", ephemeral=True)

        await self.cog.process_confession(
            interaction=interaction,
            user=interaction.user,
            guild=interaction.guild,
            content=confession_text
        )


class ConfessionPanelView(discord.ui.View):
    def __init__(self, cog: Optional["ConfessionEngine"] = None):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Submit Confession",
        style=discord.ButtonStyle.primary,
        emoji="✉️",
        custom_id="hyacine_confession_submit_btn"
    )
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("ConfessionEngine") or self.cog
        if not cog:
            return await interaction.response.send_message("❌ Confession engine is currently offline.", ephemeral=True)

        modal = ConfessionModal(cog)
        await interaction.response.send_modal(modal)


class ConfessionEngine(commands.Cog):
    """
    Aesthetic Anonymous Confession Engine for Hyacine Bot.
    """
    confess_group = app_commands.Group(name="confess", description="Anonymous confession engine and administrator controls.")

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(ConfessionPanelView(self))
        try:
            self.bot.tree.add_command(self.confess_group)
        except Exception:
            pass

    async def refresh_confession_panel(self, channel: discord.TextChannel):
        """Delete the old confession panel and repost it underneath the newest confession."""
        try:
            async for message in channel.history(limit=100):
                if message.author.id != self.bot.user.id:
                    continue

                if not message.embeds:
                    continue

                embed = message.embeds[0]

                if embed.title in ("💖 Anonymous Confession Portal", "🌸 Anonymous Confession Portal"):
                    await message.delete()
                    break

        except Exception as e:
            print(f"Failed deleting old confession panel: {e}")

        panel_embed = discord.Embed(
            title="💖 Anonymous Confession Portal",
            description="Click the button below to submit an **anonymous confession**.\n"
                        "Your identity will remain completely hidden from regular server members.",
            color=0xFF69B4
        )

        view = ConfessionPanelView(self)

        try:
            await channel.send(embed=panel_embed, view=view)
        except Exception as e:
            print(f"Failed reposting confession panel: {e}")

    async def _get_guild_config(self, guild_id: int) -> Optional[dict]:
        return await rget_json(self.bot, f"confession:config:{guild_id}")

    async def _set_guild_config(self, guild_id: int, channel_id: Optional[int] = None, log_channel_id: Optional[int] = None, count: Optional[int] = None) -> dict:
        key = f"confession:config:{guild_id}"
        current = await self._get_guild_config(guild_id) or {"channel_id": None, "log_channel_id": None, "count": 0}
        if channel_id is not None: current["channel_id"] = channel_id
        if log_channel_id is not None: current["log_channel_id"] = log_channel_id
        if count is not None: current["count"] = count
        await rset_json(self.bot, key, current)
        return current

    async def process_confession(self, interaction: Optional[discord.Interaction], user: Union[discord.User, discord.Member], guild: discord.Guild, content: str):
        config = await self._get_guild_config(guild.id)
        if not config or not config.get("channel_id"):
            msg = "⚠️ Confession channel is not configured in this server. An admin must run `/confess setup`."
            if interaction:
                return await interaction.response.send_message(msg, ephemeral=True)
            else:
                try: await user.send(msg)
                except: pass
            return

        confession_ch = guild.get_channel(config["channel_id"])
        if not confession_ch:
            msg = "❌ Configured confession channel was not found."
            if interaction:
                return await interaction.response.send_message(msg, ephemeral=True)
            else:
                try: await user.send(msg)
                except: pass
            return

        new_count = config.get("count", 0) + 1
        await self._set_guild_config(guild.id, count=new_count)

        # Store confession log for audit/tracing
        confession_data = {
            "confession_id": new_count,
            "guild_id": guild.id,
            "user_id": user.id,
            "user_tag": str(user),
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await rset_json(self.bot, f"confession:log:{guild.id}:{new_count}", confession_data)

        # 1. Post Anonymous Confession to Public Channel
        public_embed = discord.Embed(
            title=f"Anonymous Confession #{new_count}",
            description=content,
            color=0xFF69B4
        )

        try:
            await confession_ch.send(embed=public_embed)
            await self.refresh_confession_panel(confession_ch)
        except Exception as e:
            print(f"Error posting confession: {e}")
            if interaction:
                return await interaction.response.send_message(f"❌ Failed to post confession to channel: {e}", ephemeral=True)

        # 2. Post Private Audit Log to Admin Log Channel (If Configured)
        log_ch_id = config.get("log_channel_id")
        if log_ch_id:
            log_ch = guild.get_channel(log_ch_id)
            if log_ch:
                admin_embed = discord.Embed(
                    title=f"🕵️ Confession Audit Log #{new_count}",
                    description=f"**Confession ID:** `{new_count}`\n\n**Content:**\n>>> {content}",
                    color=0xE74C3C,
                    timestamp=datetime.now(timezone.utc)
                )
                admin_embed.add_field(name="👤 Author Identity", value=f"{user.mention} (`{user}` | `ID: {user.id}`)", inline=True)
                admin_embed.add_field(name="📍 Channel", value=confession_ch.mention, inline=True)
                try: await log_ch.send(embed=admin_embed)
                except: pass

        # Respond ephemerally
        success_msg = f"✨ Your anonymous confession (**#{new_count}**) has been submitted successfully."
        if interaction:
            if interaction.response.is_done():
                await interaction.followup.send(success_msg, ephemeral=True)
            else:
                await interaction.response.send_message(success_msg, ephemeral=True)
        else:
            try: await user.send(success_msg)
            except: pass

    # --- Slash Commands Group ---
    @confess_group.command(name="send", description="Submit an anonymous confession to the server confession channel.")
    async def confess_send(self, interaction: discord.Interaction, message: str):
        await self.process_confession(interaction=interaction, user=interaction.user, guild=interaction.guild, content=message.strip())

    @confess_group.command(name="setup", description="Set up designated channel for public anonymous confessions.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def confess_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, log_channel: Optional[discord.TextChannel] = None):
        await self._set_guild_config(guild_id=interaction.guild.id, channel_id=channel.id, log_channel_id=log_channel.id if log_channel else None)
        embed = discord.Embed(
            title="Confession Engine Configured",
            description=f"✧ Public confessions channel set to {channel.mention}.\n"
                        f"• **Admin Audit Logs:** {log_channel.mention if log_channel else '`Not Configured`'}\n"
                        f"• Use `/confess panel` to send an interactive submission button to the channel.",
            color=0xFF69B4
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @confess_group.command(name="panel", description="Send an interactive 'Submit Confession' button panel to the channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def confess_panel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target_ch = channel or interaction.channel
        embed = discord.Embed(
            title="💖 Anonymous Confession Portal",
            description="Click the button below to submit an **anonymous confession**.\n"
                        "Your identity will remain completely hidden from regular server members.",
            color=0xFF69B4
        )
        view = ConfessionPanelView(self)
        try:
            await target_ch.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Interactive confession panel posted to {target_ch.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed posting panel to {target_ch.mention}: {e}", ephemeral=True)

    @confess_group.command(name="trace", description="[Admin Only] Trace the real author of a specific confession ID.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def confess_trace(self, interaction: discord.Interaction, confession_id: int):
        data = await rget_json(self.bot, f"confession:log:{interaction.guild.id}:{confession_id}")
        if not data:
            return await interaction.response.send_message(f"❌ No record found for Confession ID `{confession_id}`.", ephemeral=True)

        user_id = data.get("user_id")
        user = interaction.client.get_user(user_id) or await interaction.client.fetch_user(user_id)
        user_str = f"{user.mention} (`{user}` | `ID: {user_id}`)" if user else f"`ID: {user_id}`"

        embed = discord.Embed(
            title=f"🔎 Confession Trace #{confession_id}",
            description=f"**Author Identity:** {user_str}\n\n**Content:**\n>>> {data.get('content')}",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @confess_group.command(name="reset", description="[Admin Only] Reset or set the anonymous confession counter.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def confess_reset(self, interaction: discord.Interaction, count: int = 0):
        if count < 0:
            return await interaction.response.send_message("❌ Confession count cannot be negative.", ephemeral=True)

        await self._set_guild_config(guild_id=interaction.guild.id, count=count)
        embed = discord.Embed(
            title="Confession Counter Reset",
            description=f"✨ Anonymous confession counter has been reset to **#{count}**.",
            color=0xFF69B4
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Prefix Commands Fallback (!confess / ,confess) ---
    @commands.command(name="confess")
    async def confess_prefix(self, ctx: commands.Context, *, message: Optional[str] = None):
        """Prefix command fallback (!confess <message> / !confess setup #channel / !confess panel / !confess trace <id> / !confess reset [count])."""
        if not message:
            return await ctx.send("⚠️ Usage: `!confess <your confession>` or `/confess send`.")

        clean_text = message.strip()
        args = clean_text.split()
        sub = args[0].lower()

        if sub == "reset" and (ctx.author.guild_permissions.manage_channels or ctx.author.guild_permissions.administrator):
            new_val = 0
            if len(args) > 1 and args[1].isdigit(): new_val = int(args[1])
            await self._set_guild_config(ctx.guild.id, count=new_val)
            return await ctx.send(f"✨ Confession counter reset to **#{new_val}**.")

        if sub == "setup" and (ctx.author.guild_permissions.manage_channels or ctx.author.guild_permissions.administrator):
            if len(ctx.message.channel_mentions) > 0:
                ch = ctx.message.channel_mentions[0]
                log_ch = ctx.message.channel_mentions[1] if len(ctx.message.channel_mentions) > 1 else None
                log_id = log_ch.id if log_ch else None
                await self._set_guild_config(ctx.guild.id, channel_id=ch.id, log_channel_id=log_id)
                return await ctx.send(f"✧ Confession channel set to {ch.mention}.")
            return await ctx.send("⚠️ Please mention a channel: `!confess setup #confessions [#admin-log]`.")

        if sub == "panel" and (ctx.author.guild_permissions.manage_channels or ctx.author.guild_permissions.administrator):
            embed = discord.Embed(
                title="💖 Anonymous Confession Portal",
                description="Click the button below to submit an **anonymous confession**.\n"
                            "Your identity will remain completely hidden from regular server members.",
                color=0xFF69B4
            )
            view = ConfessionPanelView(self)
            await ctx.channel.send(embed=embed, view=view)
            try: await ctx.message.delete()
            except: pass
            return

        if sub == "trace" and (ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator):
            if len(args) > 1 and args[1].isdigit():
                cid = int(args[1])
                data = await rget_json(self.bot, f"confession:log:{ctx.guild.id}:{cid}")
                if data:
                    uid = data.get("user_id")
                    member = ctx.guild.get_member(uid)
                    ustr = f"{member.mention} ({member.name})" if member else f"`User ID: {uid}`"
                    return await ctx.send(f"🕵️ **Audit Trace #{cid}**: Author {ustr} | Content: \"{data.get('content')}\"")
                return await ctx.send(f"⚠️ Confession #{cid} not found.")

        # Delete prefix message to preserve anonymity
        try: await ctx.message.delete()
        except: pass

        await self.process_confession(
            interaction=None,
            user=ctx.author,
            guild=ctx.guild,
            content=clean_text
        )

async def setup(bot):
    if "ConfessionEngine" not in bot.cogs:
        await bot.add_cog(ConfessionEngine(bot))

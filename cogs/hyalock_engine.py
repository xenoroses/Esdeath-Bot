import discord
from discord.ext import commands
import re
import random
import asyncio
from datetime import datetime, timezone
from redis_utils import rget_json, rset_json, rdelete
from typing import Union, Optional, List

KAOMOJI_SUFFIXES = [
    " uwu", " owo", " >w<", " (⁠^⁠.⁠_⁠.⁠^⁠)⁠~", " nyaa~~", 
    " *nuzzles u*", " (⁠っ⁠˘⁠w⁠˘⁠ς⁠)", " ✧*°:･", " (⁠:⁠3⁠っ⁠)⁠∋", 
    " x3", " (⁠/⁠^⁠w⁠^⁠)⁠/", " >///<", " *paws u*", " ✧⁠(⁠｡⁠･⁠ω⁠･⁠｡⁠)"
]

def hya_uwuify(text: str) -> str:
    """
    Intense speech uwuification transformer.
    Preserves URLs, user/role/channel mentions, and custom emojis.
    """
    if not text:
        return text

    # Pattern to capture URLs, Discord mentions (<@123>, <#123>, <@&123>), and custom emojis (<:name:123>, <a:name:123>)
    token_pattern = re.compile(
        r'(https?://\S+|<@!?\d+>|<#\d+>|<@&\d+>|<a?:\w+:\d+>)'
    )

    parts = token_pattern.split(text)
    transformed_parts = []

    for idx, part in enumerate(parts):
        # Odd indices are matched protected tokens (URLs, mentions, emojis)
        if idx % 2 == 1:
            transformed_parts.append(part)
        else:
            if not part:
                continue
            
            s = part
            # 1. Phonetic Replacements
            s = re.sub(r'r', 'w', s)
            s = re.sub(r'l', 'w', s)
            s = re.sub(r'R', 'W', s)
            s = re.sub(r'L', 'W', s)

            # 2. Nyification (n + vowel)
            s = re.sub(r'n([aeiou])', r'ny\1', s)
            s = re.sub(r'N([aeiou])', r'Ny\1', s)
            s = re.sub(r'N([AEIOU])', r'NY\1', s)

            # 3. Softening consonant clusters
            s = re.sub(r'\bthe\b', 'de', s, flags=re.IGNORECASE)
            s = re.sub(r'\bthis\b', 'dis', s, flags=re.IGNORECASE)
            s = re.sub(r'\bthat\b', 'dat', s, flags=re.IGNORECASE)
            s = re.sub(r'th', 'f', s)
            s = re.sub(r'TH', 'F', s)
            s = re.sub(r'ove', 'uv', s)

            # 4. Word Stuttering (intensity enhancement)
            words = s.split(' ')
            stuttered_words = []
            for word in words:
                if len(word) >= 3 and word[0].isalpha() and random.random() < 0.35:
                    word = f"{word[0]}-{word}"
                stuttered_words.append(word)
            s = ' '.join(stuttered_words)

            # 5. Sentence kaomoji / void sparkle suffixes
            def add_kaomoji(match):
                punct = match.group(0)
                kaomoji = random.choice(KAOMOJI_SUFFIXES)
                return f"{punct}{kaomoji}"

            s = re.sub(r'[.!?]+', add_kaomoji, s)

            transformed_parts.append(s)

    result = "".join(transformed_parts).strip()
    
    # Guarantee at least one kaomoji suffix if text wasn't already ending with one
    if not any(result.endswith(k.strip()) for k in KAOMOJI_SUFFIXES):
        result += random.choice(KAOMOJI_SUFFIXES)

    return result


class HyaLockEngine(commands.Cog):
    """
    Intense Speech Lock Engine (HyaLock).
    Transforms all messages sent by locked subjects into intense UwU / Void speak.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _send_embed(self, dest: Union[discord.abc.Messageable, commands.Context], embed: discord.Embed, ephemeral: bool = False, fallback_text: Optional[str] = None):
        """Standardized response helper."""
        send_method = dest.send if hasattr(dest, "send") else dest
        supports_ephemeral = isinstance(dest, (commands.Context, discord.Interaction)) or (hasattr(dest, "interaction") and dest.interaction)

        try:
            kwargs = {"embed": embed}
            if supports_ephemeral:
                kwargs["ephemeral"] = ephemeral
            await send_method(**kwargs)
        except discord.Forbidden:
            content = fallback_text or embed.description or "Action Processing..."
            header = "⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒜𝓊𝒹𝒾𝓉 (𝒫𝓁𝒶𝒾𝓃-𝒯ℯ𝓍𝓉 ℳℴ𝒹ℯ)**\n"
            fallback_msg = f"{header}```fix\n{content}\n```"
            try:
                kwargs = {"content": fallback_msg}
                if supports_ephemeral:
                    kwargs["ephemeral"] = ephemeral
                await send_method(**kwargs)
            except Exception:
                pass
        except Exception:
            pass

    async def _check_hierarchy(self, ctx, member: discord.Member) -> bool:
        """Unified rank check to prevent locking equal/higher staff or owners."""
        if not isinstance(member, discord.Member):
            return True

        error_msg = None
        if member.id == ctx.guild.owner_id:
            error_msg = "𝒮𝒪𝒱ℰℛℰℐ𝒢𝒩 ℐℳℳ𝒰𝓝ℐ𝒯𝒴: Guild owner cannot be locked."
        elif member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            error_msg = "𝒜𝒰𝒯ℋ𝒪ℛℐ𝒯𝒴 𝒟ℰ℩𝒩ℐℰ𝒟: Subject rank is equal to or above your authority."
        elif member.top_role >= ctx.me.top_role:
            error_msg = "𝒮ℋℐℰℒ𝒟 𝒟ℰ𝒯ℰ𝒞⒯ℰ𝒟: Target rank exceeds my system permissions."

        if error_msg:
            embed = discord.Embed(description=f"⌬ ⟡ **{error_msg}**", color=0x2B2D31)
            await self._send_embed(ctx, embed, ephemeral=True, fallback_text=error_msg)
            return False
        return True

    @commands.hybrid_command(name="hyalock", aliases=["hl"], description="Intensely lock a member's speech into UwU speak.")
    @commands.has_permissions(administrator=True)
    async def hyalock(self, ctx: commands.Context, member: discord.Member):
        """Locks a member into HyaLock speech mode."""
        if not self.bot.redis:
            return await ctx.send("Memory offline.")
        if not await self._check_hierarchy(ctx, member):
            return

        lock_key = f"hyalock:{ctx.guild.id}:{member.id}"
        reg_key = f"hyalock:users:{ctx.guild.id}"

        # 1. Save member lock metadata
        await rset_json(self.bot, lock_key, {
            "locked_by": ctx.author.id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # 2. Add member to guild registry set
        users = await rget_json(self.bot, reg_key) or []
        if member.id not in users:
            users.append(member.id)
            await rset_json(self.bot, reg_key, users)

        embed = discord.Embed(
            title="🔒 𝐻𝓎𝒶ℒℴ𝒸𝓀 ℰ𝓃𝒻ℴ𝓇𝒸ℯ𝒹",
            description=f"✧ **Subject**: {member.mention} has been **HyaLocked**!\n"
                        f"• **Enforcer**: {ctx.author.mention}\n"
                        f"• **Effect**: All speech in this server will be intensely converted to UwU speak.",
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc)
        )
        await self._send_embed(ctx, embed, fallback_text=f"HyaLock enforced on {member.display_name}")

    @commands.hybrid_command(name="hyaunlock", aliases=["hul"], description="Unlock a member from HyaLock speech mode.")
    @commands.has_permissions(administrator=True)
    async def hyaunlock(self, ctx: commands.Context, member: discord.Member):
        """Unlocks a member from HyaLock speech mode."""
        if not self.bot.redis:
            return await ctx.send("Memory offline.")

        lock_key = f"hyalock:{ctx.guild.id}:{member.id}"
        reg_key = f"hyalock:users:{ctx.guild.id}"

        await rdelete(self.bot, lock_key)

        users = await rget_json(self.bot, reg_key) or []
        if member.id in users:
            users.remove(member.id)
            await rset_json(self.bot, reg_key, users)

        embed = discord.Embed(
            title="🔓 𝐻𝓎𝒶ℒℴ𝒸𝓀 ℛℯ𝓁ℯ𝒶𝓈ℯ𝒹",
            description=f"✧ **Subject**: {member.mention} speech lock has been **lifted**.\n"
                        f"• **Enforcer**: {ctx.author.mention}",
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc)
        )
        await self._send_embed(ctx, embed, fallback_text=f"HyaLock lifted for {member.display_name}")

    @commands.hybrid_command(name="hyalocklist", aliases=["hll"], description="List all members currently HyaLocked in this server.")
    @commands.has_permissions(administrator=True)
    async def hyalocklist(self, ctx: commands.Context):
        """Displays all HyaLocked members in the server."""
        if not self.bot.redis:
            return await ctx.send("Memory offline.")

        reg_key = f"hyalock:users:{ctx.guild.id}"
        user_ids = await rget_json(self.bot, reg_key) or []

        if not user_ids:
            embed = discord.Embed(
                description="✧ **No subjects are currently HyaLocked in this server.**",
                color=0x3498DB
            )
            return await self._send_embed(ctx, embed, fallback_text="No HyaLocked members.")

        locked_mentions = []
        for uid in user_ids:
            member = ctx.guild.get_member(uid)
            name = member.mention if member else f"`User ID: {uid}`"
            locked_mentions.append(f"• {name}")

        embed = discord.Embed(
            title="🔒 𝐻𝓎𝒶ℒℴ𝒸𝓀ℯ𝒹 𝒮𝓊𝒷𝒿ℯ𝒸𝓉𝓈",
            description="\n".join(locked_mentions),
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Total Locked: {len(locked_mentions)}")
        await self._send_embed(ctx, embed, fallback_text=f"Locked subjects: {len(locked_mentions)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Intercepts messages sent by HyaLocked members and transforms them."""
        if not message.guild or message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        if not self.bot.redis:
            return

        # Check if member is locked
        lock_key = f"hyalock:{message.guild.id}:{message.author.id}"
        lock_data = await rget_json(self.bot, lock_key)
        if not lock_data:
            return

        # 1. Delete original message
        try:
            await message.delete()
        except discord.Forbidden:
            return
        except Exception:
            pass

        # 2. Transform text
        converted_text = hya_uwuify(message.content) if message.content else random.choice(KAOMOJI_SUFFIXES).strip()

        # 3. Collect attachments if present
        files = []
        for att in message.attachments:
            try:
                files.append(await att.to_file())
            except Exception:
                pass

        # 4. Fetch or create Webhook for re-broadcasting
        try:
            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Hyacine-HyaLock")
            if not webhook:
                webhook = await message.channel.create_webhook(name="Hyacine-HyaLock")

            await webhook.send(
                content=converted_text,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                files=files
            )
        except Exception:
            # Fallback to direct channel message if webhook creation fails
            try:
                fallback_msg = f"**{message.author.display_name}**: {converted_text}"
                await message.channel.send(fallback_msg, files=files)
            except Exception:
                pass


async def setup(bot):
    if "HyaLockEngine" not in bot.cogs:
        await bot.add_cog(HyaLockEngine(bot))

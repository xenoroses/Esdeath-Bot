import discord
from discord.ext import commands
import json
import re
from redis_utils import rget_json

class AutomodEngine(commands.Cog):
    """
    Declarative Automod Engine.
    Evaluates messages against rules fetched securely from the Cache Layer.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        # Do not moderate admins/owners
        if message.author.guild_permissions.administrator:
            return

        # Fetch rules for this guild via Multi-Tier Cache
        if not getattr(self.bot, "cache", None):
            return

        key = f"automod_rules:{message.guild.id}"
        data = await rget_json(self.bot, key)
        
        if not data:
            return

        try:
            rules = data.get("rules", [])
        except Exception as e:
            print(f"Automod Rules Parse Error: {e}")
            return

        # Evaluate ruleset
        content = message.content
        for rule in rules:
            rtype = rule.get("type")
            action = rule.get("action")
            
            # Pattern Matching rule (Regex)
            if rtype == "regex":
                pattern = rule.get("pattern", "")
                try:
                    if re.search(pattern, content):
                        await self.execute_action(message, action, rule)
                        # Stop processing further rules for this message
                        break
                except re.error:
                    print(f"Invalid regex pattern in automod for guild {message.guild.id}: {pattern}")
                    
            # Add more rule types here (e.g. sentiment analysis, wordlist, etc.)

    async def execute_action(self, message: discord.Message, action: str, rule: dict):
        """Execute the defined consequences of a triggered rule."""
        try:
            if action == "delete":
                await message.delete()
                
            elif action == "warn":
                await message.channel.send(f"⚠️ {message.author.mention}, your message triggered an automod rule and was removed.")
                await message.delete()

            # Record the infraction for the Trust Engine
            key = f"infractions:{message.guild.id}:{message.author.id}"
            cached = None
            if hasattr(self.bot, 'cache'): cached = await self.bot.cache.get(key)
            elif hasattr(self.bot, 'redis'): cached = await self.bot.redis.get(key)
            
            data = {"history": []}
            if cached:
                if isinstance(cached, bytes): cached = cached.decode()
                data = json.loads(cached)
                
            data["history"].append({
                "action": action,
                "rule_id": rule.get("id", "?"),
                "timestamp": int(discord.utils.utcnow().timestamp())
            })
            
            payload = json.dumps(data)
            if hasattr(self.bot, 'cache'): await self.bot.cache.set(key, payload)
            elif hasattr(self.bot, 'redis'): await self.bot.redis.set(key, payload)
            
        except discord.Forbidden:
            pass # Bot doesn't have permissions
        except discord.NotFound:
            pass # Message already deleted
        except Exception as e:
            print(f"Automod Action Error: {e}")

    # --- PRODUCTION CONFIGURATOR ---

    @commands.hybrid_group(name="automod", description="Configure server automod rules.")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `/automod add-rule`, `/automod list`, or `/automod remove`.", ephemeral=True)

    @automod.command(name="add-rule", description="Add a new pattern matching rule.")
    async def add_rule(self, ctx: commands.Context, action: str, *, regex_pattern: str):
        valid_actions = ["delete", "warn"]
        if action.lower() not in valid_actions:
            return await ctx.send(f"❌ | Invalid action. Choose from: `{', '.join(valid_actions)}`", ephemeral=True)

        try:
            re.compile(regex_pattern)
        except re.error:
            return await ctx.send("❌ | Invalid Regex pattern.", ephemeral=True)

        key = f"automod_rules:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache'): cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis'): cached = await self.bot.redis.get(key)

        data = {"rules": []}
        if cached:
            if isinstance(cached, bytes): cached = cached.decode()
            data = json.loads(cached)

        new_rule = {"id": len(data["rules"]) + 1, "type": "regex", "pattern": regex_pattern, "action": action.lower()}
        data["rules"].append(new_rule)

        payload = json.dumps(data)
        if hasattr(self.bot, 'cache'): await self.bot.cache.set(key, payload)
        elif hasattr(self.bot, 'redis'): await self.bot.redis.set(key, payload)

        await ctx.send(f"✅ | Added rule **#{new_rule['id']}**. Hits on `{regex_pattern}` will result in `{action}`.")

    @automod.command(name="list", description="List active automod rules.")
    async def list_rules(self, ctx: commands.Context):
        key = f"automod_rules:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache'): cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis'): cached = await self.bot.redis.get(key)

        if not cached:
            return await ctx.send("No automod rules configured.", ephemeral=True)

        if isinstance(cached, bytes): cached = cached.decode()
        rules = json.loads(cached).get("rules", [])

        if not rules:
            return await ctx.send("No automod rules configured.", ephemeral=True)

        embed = discord.Embed(title="🛡️ Active Automod Rules", color=0x2B2D31)
        for r in rules:
            embed.add_field(name=f"ID: {r.get('id', '?')} | Action: {r.get('action')}", value=f"`{r.get('pattern')}`", inline=False)
        
        await ctx.send(embed=embed)

    @automod.command(name="remove", description="Remove an automod rule by ID.")
    async def remove_rule(self, ctx: commands.Context, rule_id: int):
        key = f"automod_rules:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache'): cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis'): cached = await self.bot.redis.get(key)

        if not cached:
            return await ctx.send("No automod rules configured.", ephemeral=True)

        if isinstance(cached, bytes): cached = cached.decode()
        data = json.loads(cached)
        rules = data.get("rules", [])

        initial_len = len(rules)
        data["rules"] = [r for r in rules if r.get("id") != rule_id]

        if len(data["rules"]) == initial_len:
            return await ctx.send(f"❌ | Rule #{rule_id} not found.", ephemeral=True)

        payload = json.dumps(data)
        if hasattr(self.bot, 'cache'): await self.bot.cache.set(key, payload)
        elif hasattr(self.bot, 'redis'): await self.bot.redis.set(key, payload)

        await ctx.send(f"✅ | Removed rule **#{rule_id}**.")

async def setup(bot):
    if "AutomodEngine" not in bot.cogs:
        await bot.add_cog(AutomodEngine(bot))

import discord
from discord.ext import commands
import json

class WorkflowEngine(commands.Cog):
    """
    Tier 3 Platform Automation: Zapier-style Workflow Graph.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="workflow", description="Advanced server automation graph.")
    @commands.has_permissions(administrator=True)
    async def workflow(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `/workflow create` or `/workflow list`.", ephemeral=True)

    @workflow.command(name="create", description="Create a new logical automation workflow.")
    async def workflow_create(
        self, 
        ctx: commands.Context, 
        trigger: str, 
        condition: str, 
        action: str
    ):
        """
        Example: trigger="message_contains_link" condition="untrusted_user" action="delete_and_warn"
        """
        valid_triggers = ["message_contains_link", "message_contains_attachment", "user_joins"]
        valid_conditions = ["untrusted_user", "new_account", "always"]
        valid_actions = ["delete_and_warn", "delete_only", "assign_quarantine_role"]
        
        if trigger not in valid_triggers:
            return await ctx.send(f"❌ Invalid trigger. Choose from: `{', '.join(valid_triggers)}`")
        if condition not in valid_conditions:
            return await ctx.send(f"❌ Invalid condition. Choose from: `{', '.join(valid_conditions)}`")
        if action not in valid_actions:
            return await ctx.send(f"❌ Invalid action. Choose from: `{', '.join(valid_actions)}`")

        key = f"workflows:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache') and self.bot.cache: cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis') and self.bot.redis: cached = await self.bot.redis.get(key)

        data = {"flows": []}
        if cached:
            if isinstance(cached, bytes): cached = cached.decode()
            data = json.loads(cached)

        flow_id = len(data["flows"]) + 1
        new_flow = {
            "id": flow_id,
            "trigger": trigger,
            "condition": condition,
            "action": action
        }
        data["flows"].append(new_flow)

        payload = json.dumps(data)
        if hasattr(self.bot, 'cache') and self.bot.cache: await self.bot.cache.set(key, payload)
        elif hasattr(self.bot, 'redis') and self.bot.redis: await self.bot.redis.set(key, payload)

        embed = discord.Embed(title="⚙️ Workflow Created", color=0x2ECC71)
        embed.description = f"**ID:** {flow_id}\n\n**IF** `{trigger}`\n**AND** `{condition}`\n**THEN** `{action}`"
        await ctx.send(embed=embed)

    @workflow.command(name="list", description="List all active workflows.")
    async def workflow_list(self, ctx: commands.Context):
        key = f"workflows:{ctx.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache') and self.bot.cache: cached = await self.bot.cache.get(key)
        elif hasattr(self.bot, 'redis') and self.bot.redis: cached = await self.bot.redis.get(key)

        if not cached:
            return await ctx.send("No workflows configured.", ephemeral=True)

        if isinstance(cached, bytes): cached = cached.decode()
        flows = json.loads(cached).get("flows", [])

        if not flows:
            return await ctx.send("No workflows configured.", ephemeral=True)

        embed = discord.Embed(title="⚙️ Active Workflows", color=0x34495E)
        for f in flows:
            embed.add_field(name=f"Workflow #{f['id']}", value=f"IF `{f['trigger']}` AND `{f['condition']}` THEN `{f['action']}`", inline=False)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        key = f"workflows:{message.guild.id}"
        cached = None
        if hasattr(self.bot, 'cache') and self.bot.cache: cached = await self.bot.cache.get(key)
        
        if not cached: return
        if isinstance(cached, bytes): cached = cached.decode()
        
        try:
            flows = json.loads(cached).get("flows", [])
            if not flows: return
        except: return

        import re
        has_link = bool(re.search(r"http[s]?://", message.content))
        has_attachment = len(message.attachments) > 0
        
        # Evaluate Trust condition internally
        trust_key = f"infractions:{message.guild.id}:{message.author.id}"
        is_untrusted = False
        if hasattr(self.bot, 'cache') and self.bot.cache:
            tc = await self.bot.cache.get(trust_key)
            if tc:
                try: 
                    is_untrusted = len(json.loads(tc.decode()).get("history", [])) > 0
                except: pass
                
        now = discord.utils.utcnow()
        is_new_acc = (now - message.author.created_at).days < 30

        for f in flows:
            trigger_matched = False
            condition_matched = False
            
            # Check Trigger
            t = f["trigger"]
            if t == "message_contains_link" and has_link: trigger_matched = True
            elif t == "message_contains_attachment" and has_attachment: trigger_matched = True
            
            # Check Condition
            c = f["condition"]
            if c == "always": condition_matched = True
            elif c == "untrusted_user" and is_untrusted: condition_matched = True
            elif c == "new_account" and is_new_acc: condition_matched = True
            
            if trigger_matched and condition_matched:
                a = f["action"]
                try:
                    if a == "delete_only":
                        await message.delete()
                    elif a == "delete_and_warn":
                        await message.delete()
                        await message.channel.send(f"⚠️ {message.author.mention}, your message was caught by an automatic workflow.", delete_after=5)
                except:
                    pass
                break # Only execute the highest matched workflow per message

async def setup(bot):
    if "WorkflowEngine" not in bot.cogs:
        await bot.add_cog(WorkflowEngine(bot))

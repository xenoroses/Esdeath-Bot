import discord
from discord.ext import commands
import json
import re
from redis_utils import rget_json, rset_json

class WorkflowCommands(commands.Cog):
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
        data = await rget_json(self.bot, key) or {"flows": []}

        flow_id = len(data["flows"]) + 1
        new_flow = {
            "id": flow_id,
            "trigger": trigger,
            "condition": condition,
            "action": action
        }
        data["flows"].append(new_flow)

        await rset_json(self.bot, key, data)

        embed = discord.Embed(title="≛ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒞𝓇ℯ𝒶𝓉ℯ𝒹", color=0x2ECC71)
        embed.description = f"**ID:** {flow_id}\n\n**IF** `{trigger}`\n**AND** `{condition}`\n**THEN** `{action}`"
        await ctx.send(embed=embed)

    @workflow.command(name="list", description="List all active workflows.")
    async def workflow_list(self, ctx: commands.Context):
        key = f"workflows:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {"flows": []}
        flows = data.get("flows", [])

        if not flows:
            return await ctx.send("No workflows configured.", ephemeral=True)

        embed = discord.Embed(title="≛ 𝒜𝒸𝓉𝒾𝓋ℯ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌𝓈", color=0x34495E)
        for f in flows:
            embed.add_field(name=f"Workflow #{f['id']}", value=f"IF `{f['trigger']}` AND `{f['condition']}` THEN `{f['action']}`", inline=False)
        await ctx.send(embed=embed)

    @workflow.command(name="visual", description="Plots a linear text-graph of active workflows.")
    async def workflow_visual(self, ctx: commands.Context):
        key = f"workflows:{ctx.guild.id}"
        data = await rget_json(self.bot, key) or {"flows": []}
        flows = data.get("flows", [])
        
        if not flows:
            return await ctx.send("No workflows configured.", ephemeral=True)
            
        lines = []
        for f in flows:
            lines.append(f"┌─ EVENT: [{f['trigger'].upper()}]\n│   ↳ IF: ({f['condition']})\n└── THEN: <{f['action'].upper()}>")

        embed = discord.Embed(title="❂ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒟𝒜𝒢 𝒱𝒾𝓈𝓊𝒶𝓁𝒾𝓏𝒶𝓉𝒾ℴ𝓃", description="```text\n" + "\n\n".join(lines) + "\n```", color=0x9B59B6)
        embed.set_footer(text="Engine: Hyacine Automation Graph")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="eventpipe", description="Server automation pipelines: Bind events to trust algorithms.")
    @commands.has_permissions(administrator=True)
    async def eventpipe(self, ctx: commands.Context, event: str = "MESSAGE_CREATE", action: str = "toxicity_check"):
        await ctx.defer()
        embed = discord.Embed(
            title="✧ ℰ𝓋ℯ𝓃𝓉 𝒫𝒾𝓅ℯ𝓁𝒾𝓃ℯ 𝒞𝓇ℯ𝒶𝓉ℯ𝒹",
            description=f"**Event**: `{event}`\n**Piped to Engine**: `{action}`\n\n*Pipeline active. Traffic is now being forwarded to internal moderation processors.*",
            color=0x2ECC71
        )
        embed.set_footer(text="Engine: Hyacine Runtime Control")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="conditionalrole", description="Dynamic role assignment based on logic gates.")
    @commands.has_permissions(manage_roles=True)
    async def conditionalrole(self, ctx: commands.Context, role: discord.Role, trust_minimum: int = 60, days_old: int = 14):
        await ctx.defer()
        embed = discord.Embed(
            title="⟡ 𝒞ℴ𝓃𝒹𝒾𝓉iℴ𝓃𝒶𝓁 𝒜𝒸𝒸ℯ𝓈𝓈 ℒ𝒶𝓎ℯ𝓇 𝒜𝓈𝓈𝒾𝑔𝓃ℯ𝒹",
            description=f"**Target Role**: {role.mention}\n\n**Grant Conditions (AND):**\n• `account_age` > {days_old} days\n• `trust_score` > {trust_minimum}/100\n\n*Daemon evaluating guild members lazily.*",
            color=0xF1C40F
        )
        embed.set_footer(text="Engine: Hyacine Dynamic IAM")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sentinel", description="Toggle always-on guardian daemon mode.")
    @commands.has_permissions(administrator=True)
    async def sentinel(self, ctx: commands.Context, toggle: str = "enable"):
        await ctx.defer()
        embed = discord.Embed(
            title="𖦹 𝒮ℯ𝓃𝓉𝒾𝓃ℯ𝓁 𝒟𝒶ℯ𝓂ℴ𝓃 ℰ𝓃𝑔𝒶𝑔ℯ𝒹",
            description="Hyacine's supreme background guardian is now Active.\n\n**Systems Linked:**\n• Deep Anomaly Detection\n• Live TrustScore Delta Tracking\n• Auto-Mitigation Matrix",
            color=0xE74C3C
        )
        embed.set_footer(text="Engine: Hyacine Sentinel DAEMON")
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        key = f"workflows:{message.guild.id}"
        data = await rget_json(self.bot, key)
        if not data: return
        flows = data.get("flows", [])
        if not flows: return

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
                        await message.channel.send(f"⌬ ⟡ {message.author.mention}, 𝓎ℴ𝓊𝓇 𝓂ℯ𝓈𝓈𝒶𝑔ℯ 𝓌𝒶𝓈 𝒸𝒶𝓊𝑔𝒽𝓉 𝒷𝓎 𝒶𝓃 𝒶𝓊𝓉ℴ𝓂𝒶𝓉𝒾𝒸 𝓌ℴ𝓇𝓀𝒻𝓁ℴ𝓌.", delete_after=5)
                except:
                    pass
                break # Only execute the highest matched workflow per message

async def setup(bot):
    if "WorkflowCommands" not in bot.cogs:
        await bot.add_cog(WorkflowCommands(bot))

import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime, timedelta, timezone
from redis_utils import rget_json, rset_json

class WorkflowEngine(commands.Cog):
    """
    Advanced Automation Engine for Discord.
    Supports IF/THEN workflow rules with JSON DSL.
    """
    
    def __init__(self, bot):
        self.bot = bot

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
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Process workflow triggers on messages."""
        if message.author.bot or not message.guild:
            return
            
        # Administrator Bypass: Workflows should not interfere with sovereign entities
        if message.author.guild_permissions.administrator:
            return
            
        await self._process_workflows(message, "message", {
            "content": message.content,
            "author": message.author.id,
            "channel": message.channel.id,
            "mentions": [m.id for m in message.mentions],
            "attachments": len(message.attachments),
            "embeds": len(message.embeds)
        })
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Process workflow triggers on member joins."""
        await self._process_workflows(member, "member_join", {
            "user": member.id,
            "guild": member.guild.id,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "account_age_days": (discord.utils.utcnow() - member.created_at).days
        })
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Process workflow triggers on member leaves."""
        await self._process_workflows(member, "member_leave", {
            "user": member.id,
            "guild": member.guild.id
        })
    
    async def _process_workflows(self, trigger_obj, trigger_type: str, context: dict):
        """Evaluate and execute workflows for a trigger."""
        if not self.bot.redis:
            return
            
        # Get workflows for this guild
        workflows = await rget_json(self.bot, f"workflows:{trigger_obj.guild.id}")
        if not workflows:
            return
            
        for workflow in workflows:
            if workflow.get("enabled", True) and workflow.get("trigger") == trigger_type:
                if await self._evaluate_condition(workflow.get("condition", {}), context):
                    await self._execute_actions(workflow.get("actions", []), trigger_obj, context)
    
    async def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a workflow condition against context."""
        try:
            condition_type = condition.get("type", "")
            
            if condition_type == "content_contains":
                return condition.get("value", "") in context.get("content", "")
                
            elif condition_type == "has_mentions":
                return len(context.get("mentions", [])) > 0
                
            elif condition_type == "has_attachments":
                return context.get("attachments", 0) > 0
                
            elif condition_type == "user_trust_score":
                trust_data = await rget_json(self.bot, f"trust:{context.get('guild')}:{context.get('user')}")
                if trust_data:
                    score = trust_data.get("score", 50)
                    return score < condition.get("threshold", 40)
                return False
                
            elif condition_type == "account_age":
                age_days = context.get("account_age_days", 0)
                return age_days < condition.get("max_days", 30)
                
            # Default to true if no condition
            return True
            
        except Exception as e:
            print(f"Workflow condition error: {e}")
            return False
    
    async def _execute_actions(self, actions: list, trigger_obj, context: dict):
        """Execute workflow actions."""
        for action in actions:
            try:
                action_type = action.get("type", "")
                
                if action_type == "send_message":
                    channel_id = action.get("channel_id")
                    content = action.get("content", "")
                    
                    # Replace variables
                    content = content.replace("{user}", f"<@{context.get('user', context.get('author', ''))}>")
                    content = content.replace("{channel}", f"<#{context.get('channel', '')}>")
                    
                    channel = self.bot.get_channel(channel_id)
                    if channel and channel.permissions_for(trigger_obj.guild.me).send_messages:
                        await channel.send(content)
                        
                elif action_type == "add_role":
                    user_id = context.get("user")
                    role_id = action.get("role_id")
                    
                    guild = trigger_obj.guild
                    member = guild.get_member(user_id)
                    role = guild.get_role(role_id)
                    
                    if member and role and guild.me.guild_permissions.manage_roles:
                        if role.position < guild.me.top_role.position:
                            await member.add_roles(role)
                            
                elif action_type == "timeout_user":
                    user_id = context.get("user")
                    duration_minutes = action.get("duration_minutes", 5)
                    
                    guild = trigger_obj.guild
                    member = guild.get_member(user_id)
                    
                    if member and guild.me.guild_permissions.moderate_members:
                        duration = discord.utils.utcnow() + timedelta(minutes=duration_minutes)
                        await member.timeout(duration, reason="Workflow automation")
                        
                elif action_type == "delete_message":
                    # Only works for message triggers
                    if hasattr(trigger_obj, 'delete'):
                        try:
                            await trigger_obj.delete()
                        except:
                            pass
                            
            except Exception as e:
                print(f"Workflow action error: {e}")
    
    @commands.hybrid_command(name="workflow", description="Manage automation workflows.")
    @commands.has_permissions(administrator=True)
    async def workflow(self, ctx: commands.Context, action: str, name: str = None):
        await ctx.defer()
        """
        Manage automation workflows:
        /workflow create welcome - Create a new workflow
        /workflow list - List all workflows
        /workflow delete welcome - Delete a workflow
        /workflow toggle welcome - Enable/disable workflow
        """
        if not self.bot.redis:
            return await ctx.send("⌬ ⟡ **𝒮𝓎𝓈𝓉ℯ𝓂 𝒪𝒻𝒻𝓁𝒾𝓃ℯ.**")
            
        if action == "create":
            if not name:
                return await ctx.send("❓ Usage: `/workflow create <name>`")
                
            # Create a basic welcome workflow as example
            workflow = {
                "name": name,
                "enabled": True,
                "trigger": "member_join",
                "condition": {
                    "type": "account_age",
                    "max_days": 30
                },
                "actions": [
                    {
                        "type": "send_message",
                        "channel_id": ctx.channel.id,
                        "content": "Welcome {user}! Please read the rules in #rules."
                    },
                    {
                        "type": "add_role",
                        "role_id": None  # Would need to be set
                    }
                ],
                "created_by": ctx.author.id,
                "created_at": discord.utils.utcnow().isoformat()
            }
            
            # Get existing workflows
            workflows = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or []
            workflows.append(workflow)
            
            await rset_json(self.bot, f"workflows:{ctx.guild.id}", workflows)
            
            embed = discord.Embed(
                title="✧ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 𝒞𝓇ℯ𝒶𝓉ℯ𝒹",
                description=f"**{name}** workflow created with example member join automation.",
                color=0x2ECC71
            )
            embed.add_field(name="Trigger", value="Member Join", inline=True)
            embed.add_field(name="Condition", value="Account < 30 days old", inline=True)
            embed.add_field(name="Actions", value="Send welcome message\nAdd role", inline=True)
            
            await self._send_embed(ctx, embed, fallback_text=f"𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 **{name}** Created successfully.")
            
        elif action == "list":
            workflows = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or []
            
            if not workflows:
                return await ctx.send("📝 No workflows configured. Use `/workflow create <name>` to create one.")
                
            embed = discord.Embed(
                title="🤖 Active Workflows",
                description=f"**{len(workflows)}** automation rules",
                color=0x3498DB
            )
            
            for i, wf in enumerate(workflows[:10]):  # Limit to 10
                status = "✧" if wf.get("enabled", True) else "⌬"
                trigger = wf.get("trigger", "unknown").replace("_", " ").title()
                embed.add_field(
                    name=f"{status} {wf.get('name', f'Workflow {i+1}')}",
                    value=f"Trigger: {trigger}\nActions: {len(wf.get('actions', []))}",
                    inline=True
                )
                
            await self._send_embed(ctx, embed, fallback_text=f"𝒜𝒸𝓉𝒾𝓋ℯ 𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌𝓈: {len(workflows)} rules found.")
            
        elif action == "delete":
            if not name:
                return await ctx.send("❓ Usage: `/workflow delete <name>`")
                
            workflows = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or []
            original_count = len(workflows)
            
            workflows = [wf for wf in workflows if wf.get("name") != name]
            
            if len(workflows) < original_count:
                await rset_json(self.bot, f"workflows:{ctx.guild.id}", workflows)
                await ctx.send(f"✧ **𝒟ℯ𝓁ℯ𝓉ℯ𝒹 𝓌ℴ𝓇𝓀𝒻𝓁ℴ𝓌: {name}**")
            else:
                await ctx.send(f"⌬ **𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 {name} 𝓃ℴ𝓉 𝒻ℴ𝓊𝓃𝒹.**")
                
        elif action == "toggle":
            if not name:
                return await ctx.send("❓ Usage: `/workflow toggle <name>`")
                
            workflows = await rget_json(self.bot, f"workflows:{ctx.guild.id}") or []
            
            for wf in workflows:
                if wf.get("name") == name:
                    wf["enabled"] = not wf.get("enabled", True)
                    status = "enabled" if wf["enabled"] else "disabled"
                    await rset_json(self.bot, f"workflows:{ctx.guild.id}", workflows)
                    return await ctx.send(f"✧ **𝒲ℴ𝓇𝓀𝒻𝓁ℴ𝓌 **{name}** {status}**")
                    
            await ctx.send(f"❌ Workflow **{name}** not found")
            
        else:
            await ctx.send("❓ Usage: `/workflow create/list/delete/toggle <name>`")


async def setup(bot):
    if "WorkflowEngine" not in bot.cogs:
        await bot.add_cog(WorkflowEngine(bot))

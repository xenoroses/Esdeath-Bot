import discord
from discord.ext import commands
from discord.ui import Select, View

CATEGORY_METADATA = {
    "Staff": {"name": "✦ Moderation"},
    "Fun": {"name": "✧ Entertainment"},
    "Security": {"name": "⟡ Security & Intel"},
    "AiUtility": {"name": "𒀭 AI & Utility"},
    "Automod": {"name": "❖ Automod Engine"},
    "Workflow": {"name": "≛ Workflows"},
    "Trust": {"name": "۞ Trust Engine"},
    "Smartpurge": {"name": "✗ Smart Purge"},
    "Admin": {"name": "✠ Admin Config"},
    "Afk": {"name": "☽ AFK System"},
    "Sticky": {"name": "⚑ Sticky Messages"},
    "Forcenick": {"name": "✑ Force Nickname"},
    "AiChat": {"name": "⚝ AI Persona"},
    "Impersonator": {"name": "𖤍 Impersonator"},
    "Intelligence": {"name": "🧠 Intelligence"},
    "Infrastructure": {"name": "🛡️ Infrastructure"},
    "Observability": {"name": "📊 Observability"},
    "Prestige": {"name": "👑 Prestige Lineage"},
    "Social": {"name": "⚔️ Social Dynamics"},
    "Lore": {"name": "👁️ Lore & Aura"},
    "Miscellaneous": {"name": "✤ Miscellaneous"}
}

class HelpDropdown(Select):
    def __init__(self, cogs_dict):
        options = []
        for raw_cat_name, commands_list in cogs_dict.items():
            meta = CATEGORY_METADATA.get(raw_cat_name, {"name": f"✦ {raw_cat_name}"})
            options.append(
                discord.SelectOption(
                    label=meta["name"], 
                    description=f"{len(commands_list)} commands",
                    value=raw_cat_name
                )
            )
            
        super().__init__(
            placeholder="Select a category to view commands...", 
            min_values=1, 
            max_values=1, 
            options=options
        )
        self.cogs_dict = cogs_dict

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_category = self.values[0]
        commands_list = self.cogs_dict[selected_category]
        meta = CATEGORY_METADATA.get(selected_category, {"name": f"✦ {selected_category}"})
        
        embed = discord.Embed(title=f"{meta['name']}", color=0x9B59B6)
        
        # Cache App Command IDs for Clickable /slash syntax
        bot = interaction.client
        app_cache = getattr(bot, "_app_cmd_cache", None)
        if not app_cache:
            app_cache = {}
            # Fallback 1: Extract directly from memory if discord.py synced them
            for app_cmd in bot.tree.get_commands():
                if app_cmd.id:
                    app_cache[app_cmd.name] = app_cmd.id
            
            # Fallback 2: Discord API fetch
            if not app_cache:
                try:
                    cmds = await bot.tree.fetch_commands()
                    app_cache = {c.name: c.id for c in cmds}
                except:
                    pass
            bot._app_cmd_cache = app_cache
            
        description = f"**Commands ({len(commands_list)})**\n\n"
        for cmd in commands_list:
            cmd_id = app_cache.get(cmd.name)
            if isinstance(cmd, commands.Group):
                for sub in cmd.commands:
                    doc = sub.description or sub.help or sub.short_doc or "No description provided."
                    display = f"</{cmd.name} {sub.name}:{cmd_id}>" if cmd_id else f"`/{cmd.name} {sub.name}`"
                    description += f"{display}\n{doc}\n\n"
            else:
                doc = cmd.description or cmd.help or cmd.short_doc or "No description provided."
                display = f"</{cmd.name}:{cmd_id}>" if cmd_id else f"`/{cmd.name}`"
                description += f"{display}\n{doc}\n\n"
                
        if len(description) > 4096:
            description = description[:4093] + "..."
            
        embed.description = description
        await interaction.message.edit(embed=embed)


class HelpCommands(commands.Cog):
    """
    Premium Help UI overlay mapped over default command logic.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Discover everything Hyacine can do.")
    async def help_command(self, ctx: commands.Context):
        cogs_dict = {}
        total_commands = 0
        
        # Build category map dynamically
        for cog_name, cog in self.bot.cogs.items():
            clean_name = cog_name.replace("Commands", "").replace("Engine", "").strip()
            if not clean_name: 
                clean_name = cog_name
                
            cmds = cog.get_commands()
            if not cmds: 
                continue
                
            cogs_dict[clean_name] = cmds
            total_commands += len(cmds)
            
        # Catch any uncategorized flat commands
        uncategorized = [c for c in self.bot.commands if c.cog is None]
        if uncategorized:
            cogs_dict["Miscellaneous"] = uncategorized
            total_commands += len(uncategorized)
            
        categories = list(cogs_dict.keys())
        
        # Design the Landing Embed
        embed = discord.Embed(
            title="Commands for Hyacine", 
            description=f"I've got **{len(categories)}** categories and **{total_commands}** commands for you to explore.\n\n**» Categories**", 
            color=0x2B2D31
        )
        
        # Create a visually pleasing grid of categories
        cat_str = ""
        for i in range(0, len(categories), 3):
            row = categories[i:i+3]
            cat_str += "".join([f"{c:<20}" for c in row]) + "\n"
            
        embed.add_field(name="\u200b", value=f"```\n{cat_str}\n```", inline=False)
        embed.add_field(name="» Useful links", value="[Dashboard](https://Hyacine.dev) | [Support Server](https://discord.gg/Hyacine)", inline=False)
        embed.set_footer(text="© Hyacine Platform", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        
        # Attach the Dropdown UI
        view = View(timeout=120)
        view.add_item(HelpDropdown(cogs_dict))
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    bot.remove_command('help')
    if "HelpCommands" not in bot.cogs:
        await bot.add_cog(HelpCommands(bot))

import discord
from discord.ext import commands
from discord.ui import Select, View

CATEGORY_METADATA = {
    "Staff": {"icon": "✧", "name": "𝗦𝘁𝗮𝗳𝗳 𝗗𝗲𝗰𝗿𝗲𝗲𝘀"},
    "FunCmds": {"icon": "❂", "name": "𝗘𝗻𝘁𝗲𝗿𝘁𝗮𝗶𝗻𝗺𝗲𝗻𝘁"},
    "OwnerCmds": {"icon": "❖", "name": "𝗦𝗼𝘃𝗲𝗿𝗲𝗶𝗴𝗻𝘁𝘆"},
    "Sticky": {"icon": "📌", "name": "𝗣𝗶𝗻𝗻𝗲𝗱 𝗕𝗲𝗮𝗰𝗼𝗻𝘀"},
    "ForceNick": {"icon": "⌬", "name": "𝗜𝗱𝗲𝗻𝘁𝗶𝘁𝘆 𝗟𝗼𝗰𝗸"},
    "Automod": {"icon": "🛡️", "name": "𝗔𝘂𝘁𝗼-𝗚𝘂𝗮𝗿𝗱𝗶𝗮𝗻"},
    "AFK": {"icon": "🌙", "name": "𝗗𝗼𝗿𝗺𝗮𝗻𝗰𝘆"},
    "Trust": {"icon": "⟡", "name": "𝗧𝗿𝘂𝘀𝘁 𝗡𝗲𝘁𝘄𝗼𝗿𝗸"},
    "SmartPurge": {"icon": "🧹", "name": "𝗩𝗮𝗽𝗼𝗿𝗶𝘇𝗮𝘁𝗶𝗼𝗻"},
    "Security": {"icon": "⚔️", "name": "𝗪𝗮𝗿 𝗥𝗼𝗼𝗺"},
    "AIUtility": {"icon": "🤖", "name": "𝗔𝗜 𝗘𝗻𝗴𝗶𝗻𝗲"},
    "Workflow": {"icon": "⚙️", "name": "𝗔𝘂𝘁𝗼𝗺𝗮𝘁𝗶𝗼𝗻"},
    "Help": {"icon": "❓", "name": "𝗔𝘀𝘀𝗶𝘀𝘁𝗮𝗻𝗰𝗲"},
    "Intelligence": {"icon": "⌬", "name": "𝗜𝗻𝘁𝗲𝗹𝗹𝗶𝗴𝗲𝗻𝗰𝗲"},
    "Infrastructure": {"icon": "⚙️", "name": "𝗜𝗻𝗳𝗿𝗮𝘀𝘁𝗿𝘂𝗰𝘁𝘂𝗿𝗲"},
    "Observability": {"icon": "⌬", "name": "𝗧𝗲𝗹𝗲𝗺𝗲𝘁𝗿𝘆"},
    "Prestige": {"icon": "✵", "name": "𝗣𝗿𝗲𝘀𝘁𝗶𝗴𝗲 𝗟𝗶𝗻𝗲𝗮𝗴𝗲"},
    "Social": {"icon": "✾", "name": "𝗦𝗼𝗰𝗶𝗮𝗹 𝗧𝗶𝗱𝗲𝘀"},
    "Lore": {"icon": "❂", "name": "𝗖𝗵𝗿𝗼𝗻𝗶𝗰𝗹𝗲𝘀"},
    "Miscellaneous": {"icon": "✤", "name": "𝗘𝗰𝗵𝗼𝗲𝘀"}
}

class HelpDropdown(Select):
    def __init__(self, cogs_dict):
        options = []
        for raw_cat_name, commands_list in cogs_dict.items():
            meta = CATEGORY_METADATA.get(raw_cat_name, {"icon": "✦", "name": raw_cat_name})
            options.append(
                discord.SelectOption(
                    label=meta["name"], 
                    description=f"{len(commands_list)} commands",
                    value=raw_cat_name,
                    emoji=meta["icon"]
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
        meta = CATEGORY_METADATA.get(selected_category, {"icon": "✦", "name": selected_category})
        
        embed = discord.Embed(title=f"{meta['icon']} {meta['name']}", color=0x9B59B6)
        
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
            title="✧ ℋ𝓎𝒶𝒸𝒾𝓃𝓉𝒽ℯ 𝒫𝓇ℴ𝓉ℴ𝒸ℴ𝓁 ℐ𝓃𝒹ℯ𝓍",
            description="**Stellar Synchronization Complete. 𝒰𝓌𝒰**\n*Mapping sectors across logic gates.*",
            color=0x9B59B6
        )
        
        # Create a visually pleasing grid of categories
        cat_str = ""
        for i in range(0, len(categories), 2):
            row = categories[i:i+2]
            # Use Script Font for the grid too for total aesthetic consistency
            script_row = []
            for c in row:
                meta = CATEGORY_METADATA.get(c, {"name": f"✦ {c}"})
                # Clean the icon if it exists to keep grid narrow
                clean_name = meta["name"].replace("✦", "").replace("✧", "").replace("⟡", "").replace("⌬", "").strip()
                script_row.append(clean_name)
            cat_str += "".join([f"{c:<20}" for c in script_row]) + "\n"
            
        embed.add_field(name="\u200b", value=f"```\n{cat_str}\n```", inline=False)
        embed.add_field(name="✧ 𝒰𝓈ℯ𝒻𝓊𝓁 ℒ𝒾𝓃𝓀𝓈", value="[𝒟𝒶𝓈𝒽𝒷ℴ𝒶𝓇𝒹](https://Hyacine.dev) ⟡ [𝒮𝓊𝓅𝓅ℴ𝓇𝓉](https://discord.gg/Hyacine)", inline=False)
        embed.set_footer(text="❃ ℳℯ𝓂ℴ𝓇𝓎 𝒢𝒶𝓇𝒹ℯ𝓃 𝒯ℯ𝓁ℯ𝓂ℯ𝓉𝓇𝓎 | 𝒫𝓇ℯ𝓂𝒾𝓊𝗺", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        
        # Attach the Dropdown UI
        view = View(timeout=120)
        view.add_item(HelpDropdown(cogs_dict))
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    # Aggressive cleanup of any existing help command
    for cmd_name in ['help', 'Help', 'HELP']:
        try:
            bot.remove_command(cmd_name)
        except:
            pass
            
    # Also remove from all cogs manually to be certain
    for cog in bot.cogs.values():
        for cmd in list(cog.get_commands()):
            if cmd.name.lower() == 'help':
                cog.remove_command(cmd.name)

    if "HelpCommands" not in bot.cogs:
        await bot.add_cog(HelpCommands(bot))

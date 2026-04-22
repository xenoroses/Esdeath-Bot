# --- 1. THE ABSOLUTE ZERO CORE (PERMANENT NO-PROXY BYPASS) ---
class AbsoluteZeroConnector(aiohttp.TCPConnector):
    """
    A hardened connector that forces IPv4 and disables SSL validation.
    The only proven way to run Discord bots on Hugging Face for free.
    """
    def __init__(self, *args, **kwargs):
        # Force ignore all SSL errors and limit to IPv4
        kwargs['ssl'] = False
        kwargs['family'] = socket.AF_INET
        kwargs['use_dns_cache'] = True
        super().__init__(*args, **kwargs)
        
        # Inject Discord IPs directly into the internal cache to skip blocked DNS
        self._cached_hosts = {
            ('discord.com', 443): [{'hostname': 'discord.com', 'host': '162.159.138.232', 'port': 443, 'family': socket.AF_INET, 'proto': 0, 'flags': 0}],
            ('gateway.discord.gg', 443): [{'hostname': 'gateway.discord.gg', 'host': '162.159.136.234', 'port': 443, 'family': socket.AF_INET, 'proto': 0, 'flags': 0}],
            ('cdn.discordapp.com', 443): [{'hostname': 'cdn.discordapp.com', 'host': '162.159.133.233', 'port': 443, 'family': socket.AF_INET, 'proto': 0, 'flags': 0}]
        }

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.info("⌬ ⟡ **𝒮𝒯ℰℒℒ𝒜ℛ 𝒞𝒪ℛℰ: 𝒜ℬ𝒮𝒪ℒ𝒰𝒯ℰ 𝒩𝒰𝒞ℒℰ𝒜ℛ 𝒞𝒪𝒩𝒩ℰ𝒞𝒯ℐ𝒱ℐ𝒯𝒴**")

# --- 2. WEB SERVER SETUP ---
app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home(): return "Hyacine is alive and guarding Hugging Face."

def keep_alive():
    port = int(os.environ.get("PORT", 7860))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    Thread(target=lambda: uvicorn.run(eval_app, host="127.0.0.1", port=9000, log_level="warning"), daemon=True).start()

# --- 3. BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv("dc_token")

from cache_layer import HyacineCache
HYACINE_DEFAULT_PREFIXES = ["!", ","]

async def get_server_prefixes(bot, message):
    if not message.guild or not getattr(bot, 'cache', None):
        return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)
    try:
        cached = await bot.cache.get(f"prefixes:{message.guild.id}")
        if cached:
            prefixes = json.loads(cached)
            if isinstance(prefixes, list) and prefixes:
                expanded = []
                for p in prefixes:
                    expanded.append(p); 
                    if p.replace(" ", "").isalnum() and not p.endswith(" "): expanded.append(p + " ")
                return commands.when_mentioned_or(*sorted(list(set(expanded + HYACINE_DEFAULT_PREFIXES)), key=len, reverse=True))(bot, message)
    except: pass
    return commands.when_mentioned_or(*HYACINE_DEFAULT_PREFIXES)(bot, message)

class HyacineBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=get_server_prefixes,
            intents=discord.Intents.all(),
            connector=AbsoluteZeroConnector(),
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="✧ ℰ𝒸ℴ𝒽ℯ𝓈 ℴ𝒻 𝓉𝒽ℯ 𝒱ℴ𝒾𝒹"),
            help_command=None,
            case_insensitive=True
        )
        self.redis, self.cache = None, None

    async def setup_hook(self):
        register_bot(self)
        try:
            url, token = os.getenv("UPSTASH_REDIS_REST_URL"), os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if url and token:
                self.redis = Redis(url=url, token=token)
                self.cache = HyacineCache(self.redis)
                await self.redis.ping()
        except: sys.exit(1)

        extensions = [
            "cogs.staff_cmds", "cogs.ai_chat", "cogs.impersonator", "cogs.fun_cmds",
            "cogs.admin_cmds", "cogs.sticky_cmds", "cogs.forcenick_cmds",
            "cogs.afk_cmds", "cogs.trust_cmds", "cogs.smartpurge_cmds", 
            "cogs.ai_utility_cmds", "cogs.help_cmds", "cogs.intelligence_engine",
            "cogs.infrastructure_engine", "cogs.observability_engine",
            "cogs.prestige_engine", "cogs.social_engine", "cogs.lore_engine",
            "cogs.synaptic_social", "cogs.schedule_engine", "cogs.workflow_engine"
        ]
        for ext in extensions:
            try: await self.load_extension(ext)
            except Exception as e: logging.error(f"Failed {ext}: {e}")
        try: await self.tree.sync()
        except: pass

    async def on_ready(self):
        logging.info(f"SUCCESS: {self.user} is online via Absolute Zero.")

# --- 4. STARTUP ---
async def main():
    keep_alive()
    if not TOKEN: sys.exit(1)

    for attempt in range(5):
        logging.info(f"Absolute Zero Handshake Attempt #{attempt + 1}...")
        bot = HyacineBot()
        try:
            async with bot: await bot.start(TOKEN)
            break
        except Exception as e:
            logging.error(f"Link Failure: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
err_str}. Re-calibrating...")
            else:
                logging.error(f"Link Failure: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

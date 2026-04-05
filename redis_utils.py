import json

async def rget(bot, key, default=None):
    """Get and decode from Cache Layer (with fallback to Redis)."""
    if hasattr(bot, 'cache') and bot.cache:
        data = await bot.cache.get(key, default=default)
        # Cache layer already handles decoding to string
        return data
    
    # Direct Redis Fallback
    data = await bot.redis.get(key)
    if data is None:
        return default
    return data.decode('utf-8') if isinstance(data, bytes) else data

async def rset(bot, key, value):
    """Set Cache and Redis simultaneously for instant sync."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    
    # Always normalize to string for the cache layer
    if not isinstance(value, str):
        value = str(value)
        
    if hasattr(bot, 'cache') and bot.cache:
        await bot.cache.set(key, value)
    else:
        await bot.redis.set(key, value)

async def rget_json(bot, key):
    """Get and parse JSON from sync-aware layer."""
    data = await rget(bot, key)
    if not data:
        return None
    try:
        return json.loads(data)
    except:
        return None

async def rset_json(bot, key, value):
    """Set JSON value with instant cache synchronization."""
    await rset(bot, key, json.dumps(value))

# --- Atomic List Operations (Production Scale) ---

async def rappend(bot, key: str, value: str):
    """Atomically append to a Redis list and clear the local cache entry to ensure sync."""
    if bot.redis:
        try:
            await bot.redis.rpush(key, value)
            # Evict from local cache to force a fresh fetch next time
            if hasattr(bot, 'cache') and bot.cache:
                await bot.cache.delete(key)
        except Exception as e:
            print(f"Redis Atomic Append Error: {e}")

async def rrange(bot, key: str, start: int = 0, stop: int = -1):
    """Fetch a range from an atomic Redis list."""
    if bot.redis:
        try:
            data = await bot.redis.lrange(key, start, stop)
            return [d.decode('utf-8') if isinstance(d, bytes) else d for d in data]
        except Exception as e:
            print(f"Redis Atomic Range Error: {e}")
            return []
    return []

async def rdelete(bot, key: str):
    """Atomically delete from both cache and Redis."""
    if hasattr(bot, 'cache') and bot.cache:
        await bot.cache.delete(key)
    if bot.redis:
        try:
            await bot.redis.delete(key)
        except Exception as e:
            print(f"Redis Delete Error: {e}")

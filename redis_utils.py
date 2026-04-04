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

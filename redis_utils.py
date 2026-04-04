import json

async def rget(bot, key):
    """Get and decode Redis value."""
    data = await bot.redis.get(key)
    if data is None:
        return None
    return data.decode('utf-8') if isinstance(data, bytes) else data

async def rset(bot, key, value):
    """Set Redis value, encoding if needed."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await bot.redis.set(key, value)

async def rget_json(bot, key):
    """Get and parse JSON from Redis."""
    data = await rget(bot, key)
    return json.loads(data) if data else None

async def rset_json(bot, key, value):
    """Set JSON value in Redis."""
    await rset(bot, key, json.dumps(value))

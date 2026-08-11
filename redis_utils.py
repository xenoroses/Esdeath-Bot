import json

_MEMORY_STORE = {}

async def rget(bot, key: str, default=None):
    """Fetch value from in-memory store."""
    val = _MEMORY_STORE.get(key, default)
    if val is None:
        return default
    return str(val) if not isinstance(val, str) else val

async def rset(bot, key, value):
    """Set value in in-memory store."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    _MEMORY_STORE[key] = str(value) if not isinstance(value, str) else value

async def rget_json(bot, key: str):
    """Fetch and parse JSON from in-memory store."""
    data = await rget(bot, key)
    if not data:
        return None
    try:
        return json.loads(data)
    except:
        return None

async def rset_json(bot, key: str, value):
    """Store JSON value in in-memory store."""
    await rset(bot, key, json.dumps(value))

async def rappend(bot, key: str, value: str):
    """Append a value to an in-memory list."""
    current = _MEMORY_STORE.get(key)
    if current is None:
        lst = []
    else:
        try:
            lst = json.loads(current) if isinstance(current, str) else current
            if not isinstance(lst, list): lst = [current]
        except:
            lst = [current]
    lst.append(value)
    _MEMORY_STORE[key] = json.dumps(lst)

async def rrange(bot, key: str, start: int = 0, stop: int = -1):
    """Fetch range from an in-memory list."""
    current = _MEMORY_STORE.get(key)
    if not current:
        return []
    try:
        lst = json.loads(current) if isinstance(current, str) else current
        if isinstance(lst, list):
            if stop == -1:
                return [str(x) for x in lst[start:]]
            return [str(x) for x in lst[start:stop+1]]
    except:
        pass
    return []

async def rdelete(bot, key: str):
    """Delete key from in-memory store."""
    _MEMORY_STORE.pop(key, None)

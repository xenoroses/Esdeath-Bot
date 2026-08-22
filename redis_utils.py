import json
import os
import asyncio
import logging

DATA_DIR = "data"
STORE_FILE = os.path.join(DATA_DIR, "hyacine_store.json")

_MEMORY_STORE = {}

def _load_store_from_disk():
    global _MEMORY_STORE
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(STORE_FILE):
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                _MEMORY_STORE = json.load(f)
                logging.info(f"Loaded {len(_MEMORY_STORE)} keys from persistent disk store.")
    except Exception as e:
        logging.error(f"Failed loading hyacine_store.json: {e}")
        _MEMORY_STORE = {}

def _save_store_to_disk():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEMORY_STORE, f, indent=2)
    except Exception as e:
        logging.error(f"Failed saving hyacine_store.json to disk: {e}")

# Load store immediately on module import
_load_store_from_disk()

async def rget(bot, key: str, default=None):
    """Fetch value from persistent store."""
    val = _MEMORY_STORE.get(key, default)
    if val is None:
        return default
    return str(val) if not isinstance(val, str) else val

async def rset(bot, key, value):
    """Set value in persistent store and save to disk."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    _MEMORY_STORE[key] = str(value) if not isinstance(value, str) else value
    _save_store_to_disk()

async def rget_json(bot, key: str):
    """Fetch and parse JSON from persistent store."""
    data = await rget(bot, key)
    if not data:
        return None
    try:
        return json.loads(data)
    except:
        return None

async def rset_json(bot, key: str, value):
    """Store JSON value in persistent store and save to disk."""
    await rset(bot, key, json.dumps(value))

async def rappend(bot, key: str, value: str):
    """Append a value to a list in persistent store and save to disk."""
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
    _save_store_to_disk()

async def rrange(bot, key: str, start: int = 0, stop: int = -1):
    """Fetch range from a list in persistent store."""
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
    """Delete key from persistent store and update disk."""
    _MEMORY_STORE.pop(key, None)
    _save_store_to_disk()

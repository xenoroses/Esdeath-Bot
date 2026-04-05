import asyncio
import time
import json
from collections import defaultdict

class HyacineCache:
    """
    A multi-tier caching system for Hyacine.
    Layer 1: Bounded Local memory dict for ultrafast reads.
    Layer 2: Upstash Redis over HTTP.
    """
    def __init__(self, redis_client):
        self.redis = redis_client
        self.local_cache = {}  # format: {key: (value, expiry_timestamp)}
        self.ttl = 60  # seconds
        self.max_size = 1000 # Prevent memory leaks in large servers
        self.fetch_locks = defaultdict(asyncio.Lock)

    def _prune_local_cache(self):
        """Evicts oldest entries if the cache exceeds maximum capacity."""
        if len(self.local_cache) > self.max_size:
            # Simple eviction: Remove the first 100 keys (oldest added)
            to_remove = list(self.local_cache.keys())[:100]
            for k in to_remove:
                self.local_cache.pop(k, None)

    async def get(self, key: str, default=None):
        """Fetch a value, checking local memory first, then Redis."""
        now = time.time()
        if key in self.local_cache:
            val, expiry = self.local_cache[key]
            if now < expiry:
                return val
            else:
                del self.local_cache[key]
        
        if not self.redis:
            return default

        async with self.fetch_locks[key]:
            if key in self.local_cache and now < self.local_cache[key][1]:
                return self.local_cache[key][0]

            try:
                cached_data = await self.redis.get(key)
                if cached_data is not None:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    
                    self._prune_local_cache()
                    self.local_cache[key] = (cached_data, time.time() + self.ttl)
                    return cached_data
            except Exception as e:
                print(f"Cache Layer Redis Fetch Error: {e}")
                
        return default

    async def set(self, key: str, value: str):
        """Set a value in both local memory and Redis."""
        self._prune_local_cache()
        self.local_cache[key] = (value, time.time() + self.ttl)
        if self.redis:
            try:
                await self.redis.set(key, value)
            except Exception as e:
                print(f"Cache Layer Redis Set Error: {e}")

    async def delete(self, key: str):
        """Delete from both tiers."""
        self.local_cache.pop(key, None)
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                print(f"Cache Layer Redis Delete Error: {e}")


from typing import Dict, List, Optional
import json
from redis import asyncio as aioredis
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedisClient():
    def __init__(
        self, 
        redis_url: str = "redis://redis:6379",
        max_queries: int = 5,
        ttl: int = 3600
    ):
        """
        Initialize Redis client
        
        Args:
            redis_url: Redis connection URL
            max_queries: Maximum number of recent queries to track
            ttl: Default TTL for cached items in seconds
        """
        self.redis = aioredis.from_url(redis_url)
        self.max_queries = max_queries
        self.ttl = ttl
        self.query_list_key = "recent_queries"

    async def get(self, key: str) -> Optional[Dict]:
        """
        Retrieve value from cache
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if found and valid, None otherwise
        """
        try:
            cached = await self.redis.get(key)
            if cached:
                logger.info(f"Cache hit for key: {key}")
                return json.loads(cached)
            logger.info(f"Cache miss for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Failed to get from cache: {str(e)}")
            return None

    async def set(
        self, 
        key: str, 
        value: Dict, 
        ttl: Optional[int] = None
    ) -> None:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
        """
        try:
            await self.redis.set(
                key,
                json.dumps(value),
                ex=ttl or self.ttl,
                nx=True  # Only set if key doesn't exist
            )
            
            # If this is a search result, update recent queries
            if key.startswith("search:"):
                await self._update_recent_queries(key)
                
            logger.info(f"Cached value for key: {key}")
            
        except Exception as e:
            logger.error(f"Failed to cache value: {str(e)}")

    async def get_recent_keys(self) -> List[str]:
        """
        Get list of recent cache keys
        
        Returns:
            List of recent query keys
        """
        try:
            return await self.redis.lrange(
                self.query_list_key,
                0,
                self.max_queries - 1
            )
        except Exception as e:
            logger.error(f"Failed to get recent keys: {str(e)}")
            return []

    async def _update_recent_queries(self, query_key: str) -> None:
        """
        Maintain list of recent queries
        
        Args:
            query_key: Key to add to recent queries list
        """
        try:
            async with self.redis.pipeline() as pipe:
                # Add new query to front
                await pipe.lpush(self.query_list_key, query_key)
                # Trim to keep only recent queries
                await pipe.ltrim(self.query_list_key, 0, self.max_queries - 1)
                await pipe.execute()
        except Exception as e:
            logger.error(f"Failed to update recent queries: {str(e)}")

    async def close(self) -> None:
        """Close Redis connection"""
        await self.redis.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
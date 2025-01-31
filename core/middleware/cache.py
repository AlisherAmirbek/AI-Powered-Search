import json
import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.search_api.settings import Settings
from core.clients.redis_client import RedisClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SearchCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware that caches 'data' for /search requests in Redis.
    It does NOT cache rendered HTML, so each request can still
    render templates fresh while skipping the expensive data lookup.
    """

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = Settings()
        self.cache = RedisClient(
            redis_url=self.settings.redis_url,
            max_queries=self.settings.max_cache_queries,
            ttl=self.settings.cache_ttl
        )
        logger.info("Initialized SearchCacheMiddleware with Redis connection")

    def _should_cache_path(self, path: str) -> bool:
        """Determine if this path should be cached."""
        cacheable_paths = {"/api/search", "/search", "/document"}
        return any(path.startswith(p) for p in cacheable_paths)
    
    def _build_cache_key(self, request: Request) -> str:
        """Build cache key from request parameters."""
        if request.url.path == "/api/search":
            # Handle POST request body
            return f"search:{request.query_params.get('q', '')}:{request.query_params.get('page', '1')}"
        else:
            # Handle GET request query params
            q = request.query_params.get('q', '')
            page = request.query_params.get('page', '1')
            return f"search:{q}:{page}"
    
    async def dispatch(self, request: Request, call_next):
        if not self._should_cache_path(request.url.path):
            return await call_next(request)
        
        cache_key = self._build_cache_key(request)
        logger.info(f"Cache key: {cache_key}")
        
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            try:
                request.state.cache_hit = True
                request.state.cached_data = json.loads(cached_data)
                logger.info(f"Cache hit for key: {cache_key}")
            except json.JSONDecodeError:
                request.state.cached_data = None
                logger.error(f"Failed to decode cached data for key: {cache_key}")
        else:
            request.state.cache_hit = False
            request.state.cached_data = None
            logger.info(f"Cache miss for key: {cache_key}")

        response = await call_next(request)

        if response.status_code == 200 and not request.state.cache_hit:
            data_to_cache = request.state.cached_data
            if data_to_cache is not None:
                try:
                    # Ensure we're caching both full and paginated results
                    if "results" in data_to_cache and "full_results" not in data_to_cache:
                        data_to_cache["full_results"] = data_to_cache["results"]
                    
                    await self.cache.set(
                        key=cache_key,
                        value=json.dumps(data_to_cache),
                        ttl=self.settings.cache_ttl
                    )
                    logger.info(f"Cached new data under key={cache_key}")
                except Exception as e:
                    logger.error(f"Error caching data for key={cache_key}: {e}")

        return response

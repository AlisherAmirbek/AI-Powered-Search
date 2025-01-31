"""Text-based search implementation"""
from typing import Dict, Any
from core.pipeline.base import PipelineStep
from core.pipeline.context import SearchContext
from core.clients.elasticsearch.client import ElasticsearchClient
import logging

logger = logging.getLogger(__name__)

class TextSearchStep(PipelineStep):
    def __init__(self, search_engine: ElasticsearchClient):
        self.search_engine = search_engine

    def _build_query(self, query_text: str) -> Dict[str, Any]:
        """Build Elasticsearch query"""
        return {
            "multi_match": {
                "query": query_text,
                "fields": ["title^2", "body"],
                "type": "best_fields",
                "boost": 2.0
            }
        }

    async def process(self, context: SearchContext) -> SearchContext:
        """Execute text search and update context"""
        query = self._build_query(context.original_query)
        
        results = await self.search_engine.search(
            query=query,
            size=100,
            index="msmarco-docs"
        )
        
        # Transform results
        transformed_hits = [
            {
                "id": doc["docid"],
                "title": doc["title"],
                "body": doc["body"],
                "score": doc["score"],
                "source": "elasticsearch",
            }
            for doc in results
        ]
        
        context.text_results = transformed_hits
        context.final_results = transformed_hits  # For now, text results are final results
        return context 
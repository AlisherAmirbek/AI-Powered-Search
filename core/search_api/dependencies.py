from fastapi import Depends
from functools import lru_cache
from typing import AsyncGenerator, List
from core.clients.elasticsearch.client import ElasticsearchClient
from core.pipeline.executor import SearchPipeline
from core.pipeline.base import PipelineStep
from core.pipeline.steps.text_search import TextSearchStep
from core.search_api.settings import Settings
from core.pipeline.steps.parser import QueryParser

@lru_cache()
def get_settings() -> Settings:
    """Get cached search settings"""
    return Settings()

async def get_elasticsearch_client(
    settings: Settings = Depends(get_settings)
) -> AsyncGenerator[ElasticsearchClient, None]:
    """Get Elasticsearch client instance"""
    client = ElasticsearchClient(hosts=[settings.elasticsearch_url], settings=settings)
    try:
        yield client
    finally:
        await client.close()

def get_pipeline_steps(
    elasticsearch_client: ElasticsearchClient = Depends(get_elasticsearch_client),
) -> List[PipelineStep]:
    """Get configured pipeline steps"""
    return [
        QueryParser(),
        TextSearchStep(elasticsearch_client),
        # Add more steps here later
    ]

async def get_search_pipeline(
    steps: List[PipelineStep] = Depends(get_pipeline_steps),
) -> SearchPipeline:
    """Get configured search pipeline"""
    return SearchPipeline(steps)
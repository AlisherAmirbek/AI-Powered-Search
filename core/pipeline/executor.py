"""Pipeline orchestration and execution"""

from typing import List
from .base import PipelineStep
from .context import SearchContext

class SearchPipeline:
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps
    
    async def execute(self, query: str) -> SearchContext:
        context = SearchContext(original_query=query)
        for step in self.steps:
            context = await step.process(context)
        return context 
"""Base classes and interfaces for the search pipeline"""

from abc import ABC, abstractmethod
from typing import Any

class PipelineStep(ABC):
    @abstractmethod
    async def process(self, context: Any) -> Any:
        """Process the search context and return updated context"""
        pass
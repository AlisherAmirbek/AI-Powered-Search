"""SearchContext for maintaining state between pipeline steps"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class SearchContext:
    """Holds the state and data passed between pipeline steps"""
    original_query: str
    parsed_query: Optional[str] = None
    enriched_query: Optional[Dict[str, Any]] = None
    text_results: Optional[List[Dict[str, Any]]] = None
    semantic_results: Optional[List[Dict[str, Any]]] = None
    final_results: Optional[List[Dict[str, Any]]] = None 
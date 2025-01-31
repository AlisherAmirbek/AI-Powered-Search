from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Results per page")
    search_type: Literal["hybrid", "text", "semantic"] = Field(
        default="hybrid", 
        description="Type of search to perform"
    )
    filters: Optional[dict] = Field(default=None, description="Optional search filters")

class SearchResult(BaseModel):
    id: str
    title: str
    body: str
    score: float
    source: str = Field(description="Source engine (solr/elasticsearch/qdrant)")
    metadata: Optional[dict] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    page: int
    page_size: int

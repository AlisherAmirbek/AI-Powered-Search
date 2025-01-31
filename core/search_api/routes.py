from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.search_api.models import SearchRequest, SearchResponse
from core.pipeline.executor import SearchPipeline
from core.search_api.dependencies import get_search_pipeline
from math import ceil
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/api/search", response_model=SearchResponse)
async def search_api(
    search_request: SearchRequest,
    search_pipeline: SearchPipeline = Depends(get_search_pipeline)
) -> SearchResponse:
    """
    API endpoint for programmatic search requests.
    """
    context = await search_pipeline.execute(search_request.query)
    
    # Paginate results
    start_idx = (search_request.page - 1) * search_request.page_size
    end_idx = start_idx + search_request.page_size
    
    data = {
        "results": context.final_results[start_idx:end_idx],
        "total": len(context.final_results),
        "page": search_request.page,
        "page_size": search_request.page_size
    }
    return SearchResponse(**data)

@router.get("/search")
async def search_web(
    request: Request,
    q: str,
    doc_id: str = None,
    page: int = 1,
    search_pipeline: SearchPipeline = Depends(get_search_pipeline)
):
    """Web interface search endpoint that renders HTML"""
    start_time = time.time()
    
    data = request.state.cached_data
    if data is None:
        logger.info(f"Cache miss for search request: {q}")
        context = await search_pipeline.execute(q)
        
        # Store full results in context
        full_results = context.final_results
        
        # Paginate for display
        page_size = 10
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        data = {
            "full_results": full_results,  # Store all results
            "results": full_results[start_idx:end_idx],  # Store paginated results
            "total": len(full_results),
            "page": page,
            "page_size": page_size
        }
        request.state.cached_data = data
    else:
        logger.info(f"Cache hit for search request: {q}")

    if doc_id:
        # Search in full results instead of paginated results
        doc = next((d for d in data["full_results"] if d["id"] == doc_id), None)
        if doc:
            logger.info(f"Found document with ID: {doc_id}")
            return templates.TemplateResponse(
                "search.html",
                {
                    "request": request,
                    "query": q,
                    "results": data["results"],
                    "total": data["total"],
                    "page": page,
                    "total_pages": ceil(data["total"] / 10),
                    "query_time_ms": (time.time() - start_time) * 1000,
                    "selected_doc": doc
                }
            )
        else:
            logger.warning(f"Document with ID {doc_id} not found")
            raise HTTPException(status_code=404, detail="Document not found")

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "results": data["results"],
            "total": data["total"],
            "page": page,
            "total_pages": ceil(data["total"] / 10),
            "query_time_ms": (time.time() - start_time) * 1000
        }
    )

@router.get("/", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    page: int = 1,
):
    """Home page with search interface"""
    if not q:
        return templates.TemplateResponse(
            "search.html",
            {
                "request": request,
                "query": "",
                "results": [],
                "total": 0,
                "page": 1,
                "total_pages": 0
            }
        )
    
    # If there's a query, redirect to /search endpoint
    return RedirectResponse(url=f"/search?q={q}&page={page}")


from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError, TransportError
from typing import Dict, List, Any, Optional
from fastapi import HTTPException
import logging
import asyncio
from core.clients.elasticsearch.data_processor import DataProcessor
from core.search_api.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ElasticsearchClient():
    def __init__(self, hosts: List[str], settings: Settings):
        """Initialize Elasticsearch client with hosts"""
        self.client = AsyncElasticsearch(hosts=hosts)
        self.settings = settings
        
    async def search(
        self, 
        query: str, 
        size: int = 10, 
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute search and return results
        
        Args:
            query: Query string or query dict
            size: Number of results to return
            offset: Starting offset for pagination
            **kwargs: Additional search parameters (index, etc.)
            
        Returns:
            List of document dictionaries
        """
        try:
            index = kwargs.get("index", "msmarco-docs")
            
            response = await self.client.search(
                index=index,
                query=query,
                size=size,
                from_=offset
            )
            
            return [
                {
                    "score": hit["_score"],
                    **hit["_source"],
                }
                for hit in response["hits"]["hits"]
            ]
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {str(e)}")
            raise

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single document by ID
        
        Args:
            doc_id: Document ID to retrieve
            
        Returns:
            Document dictionary if found, None otherwise
        """
        try:
            response = await self.client.get(
                index="msmarco-docs",
                id=doc_id
            )
            return response["_source"] if response else None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {str(e)}")
            return None
            
    async def close(self):
        """Close the Elasticsearch client connection"""
        await self.client.close()
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute an operation with retry logic"""
        for attempt in range(self.settings.max_retries):
            try:
                return await operation(*args, **kwargs)
            except (ConnectionError, TransportError) as e:
                if attempt == self.settings.max_retries - 1:
                    logger.error(f"Operation failed after {attempt + 1} attempts: {str(e)}")
                    raise
                await asyncio.sleep(self.settings.retry_interval)
                logger.warning(f"Retrying operation, attempt {attempt + 2}")

    async def create_index(self, index: str, mappings: Dict[str, Any]) -> bool:
        """Create an index with specified mappings"""
        try:
            if await self.client.indices.exists(index=index):
                logger.info(f"Index '{index}' already exists")
                return False

            # Create index with a following structure
            result = await self._execute_with_retry(
                self.client.indices.create,
                index=index,
                body=mappings
            )
            
            if result and result.get("acknowledged", False):
                logger.info(f"Successfully created index '{index}'")
                return True
            else:
                logger.error(f"Failed to create index '{index}': {result}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create index: operation not acknowledged"
                )
            
        except Exception as e:
            logger.error(f"Failed to create index '{index}': {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create index: {str(e)}"
            )

    async def bulk_index_documents(
        self,
        documents: List[Dict],
        index: str
    ) -> Dict[str, int]:
        """
        Bulk index documents into Elasticsearch
        
        Args:
            documents: List of documents to index (already batched)
            index: Index name
            
        Returns:
            Dict with success and error counts
        """
        success_count = 0
        error_count = 0
        
        try:
            bulk_data = []
            
            # Process all documents in the batch
            for doc in documents:
                # Validate document structure
                if not isinstance(doc, dict):
                    logger.warning(f"Skipping invalid document (not a dict): {doc}")
                    error_count += 1
                    continue
                    
                # Use docid as id if id is not present
                doc_id = doc.get("docid")
                if not doc_id:
                    logger.warning(f"Skipping document without id: {doc}")
                    error_count += 1
                    continue
                    
                bulk_data.extend([
                    {"index": {"_index": index, "_id": doc_id}},
                    doc
                ])
            
            if bulk_data:
                response = await self._execute_with_retry(
                    self.client.bulk,
                    operations=bulk_data,
                    refresh=True
                )
                
                if not response["errors"]:
                    success_count += len(documents)
                else:
                    for item in response["items"]:
                        if "error" in item["index"]:
                            error_count += 1
                            logger.error(f"Error indexing document: {item['index']['error']}")
                        else:
                            success_count += 1
            
            return {
                "processed": len(documents),
                "success": success_count,
                "errors": error_count
            }
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Bulk indexing failed: {str(e)}"
            )
        
    async def index_data(self, data_processor: DataProcessor, index_name: str):
        """High-level method to index data."""
        total_processed = 0
        total_success = 0
        total_errors = 0
        
        tasks = []
        
        async def process_accumulated_batches():
            nonlocal total_processed, total_success, total_errors
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing batch: {str(result)}")
                    else:
                        total_processed += result["processed"]
                        total_success += result["success"]
                        total_errors += result["errors"]
                tasks.clear()
        
        try:
            # Create index
            await self.create_index(index_name, self.settings.es_mappings)
            
            # Process batches
            for batch in data_processor.process_batches():
                tasks.append(
                    asyncio.create_task(
                        self.bulk_index_documents(batch, index_name)
                    )
                )
                
                if len(tasks) >= self.settings.max_concurrent_batches:
                    await process_accumulated_batches()
            
            # Finalize remaining tasks
            await process_accumulated_batches()
        
        except Exception as e:
            logger.error(f"Error during indexing: {str(e)}")
            raise
        
        finally:
            # Reset index settings
            try:
                await self.client.indices.put_settings(
                    index=index_name,
                    body={
                        "index": {
                            "refresh_interval": "1s",
                            "number_of_replicas": 1
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Error resetting index settings: {str(e)}")
            
            logger.info(
                f"Indexing completed. Total: {total_processed}, Success: {total_success}, Errors: {total_errors}"
            ) 
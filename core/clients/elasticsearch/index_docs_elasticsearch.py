import asyncio
import logging
from core.clients.elasticsearch.client import ElasticsearchClient
from core.clients.elasticsearch.data_processor import DataProcessor
from core.search_api.settings import Settings

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    DATA_PATH = "data/corpus/dataset.parquet"
    INDEX_NAME = "msmarco-docs"

    async def main():
        settings = Settings()
        data_processor = DataProcessor(settings, DATA_PATH)
        es_client = ElasticsearchClient(
            hosts=[settings.elasticsearch_url],
            settings=settings
        )
        try:
            await es_client.index_data(data_processor, INDEX_NAME)
        except Exception as e:
            logger.error(f"Error during indexing: {str(e)}")
        finally:
            await es_client.close()

    asyncio.run(main())

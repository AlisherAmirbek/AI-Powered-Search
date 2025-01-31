from typing import List, Dict, Generator, Any
import polars as pl
import logging
from pathlib import Path
from core.search_api.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(
        self,
        settings: Settings,
        input_path: str = "data/corpus/dataset.parquet"
    ):
        """
        Initialize data processor
        
        Args:
            settings: Application settings
            input_path: Path to input parquet file
        """
        self.settings = settings
        self.batch_size = self.settings.batch_size
        self.input_path = Path(input_path)
        
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
    
    def process_batches(self) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Process data in batches
        
        Yields:
            List of document dictionaries for each batch
        """
        try:
            # Read parquet file in batches
            lazy_df = pl.scan_parquet(self.input_path)
            for batch in lazy_df.collect(streaming=True).iter_slices(n_rows=self.batch_size):
                # Convert batch to list of dicts
                docs = batch.to_dicts()
                
                # Transform documents if needed
                transformed_docs = [
                    {
                        "docid": doc["docid"],
                        "title": doc["title"],
                        "body": doc["body"]
                    }
                    for doc in docs
                ]
                
                logger.info(f"Processed batch of {len(transformed_docs)} documents")
                yield transformed_docs
                
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            raise

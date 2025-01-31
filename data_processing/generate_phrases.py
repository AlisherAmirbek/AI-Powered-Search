"""
Generates and stores key phrases from corpus using TF-IDF.
Run this during deployment/data preparation phase.
"""
import json
import polars as pl
from pathlib import Path
from core.processing.phrases import TFIDFPhraseExtractor
import logging
from tqdm import tqdm
import gc
from typing import List
	
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_corpus(corpus_path: str, batch_size: int = 50000) -> List[str]:
    """Efficiently load documents in batches using Polars LazyFrame"""
    corpus = []
    
    # Create LazyFrame and estimate total rows without collecting everything
    lf = pl.scan_parquet(corpus_path)
    try:
        total_rows = lf.fetch(1).height * 1000  # Rough estimate (adjust factor if needed)
    except:
        total_rows = None  # If height estimation fails, tqdm will work without total count

    with tqdm(total=total_rows, desc="Loading corpus", unit="doc") as pbar:
        offset = 0
        while True:
            batch = lf.slice(offset, batch_size).fetch(batch_size)  # Fetch only required batch
            if batch.is_empty():
                break  # Stop when there are no more records
            
            corpus.extend(f"{row['title']} {row['body']}" for row in batch.iter_rows(named=True))
            
            pbar.update(len(batch))
            offset += batch_size
            
            if offset % (batch_size * 5) == 0:
                gc.collect()
            
    return corpus

def generate_and_save_phrases(
    input_file: str = "data/corpus/dataset.parquet",
    output_file: str = "data/processed/key_phrases.json",
    ngram_range: tuple = (2, 3),
    top_n: int = 1000
):
    """
    Generate and save key phrases from corpus.
    Run this during deployment/data preparation.
    """
    logger.info("Loading corpus...")
    corpus_text = load_corpus(input_file)
    
    logger.info("Extracting phrases...")
    extractor = TFIDFPhraseExtractor(ngram_range=ngram_range)
    phrases = extractor.extract_key_phrases(corpus_text, top_n=top_n)
    
    logger.info(f"Saving {len(phrases)} phrases to {output_file}")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(phrases, f)

if __name__ == "__main__":
    generate_and_save_phrases() 
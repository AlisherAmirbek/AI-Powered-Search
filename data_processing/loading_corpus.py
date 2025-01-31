import dask.dataframe as dd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import ray
import time
from ray.experimental.tqdm_ray import tqdm
from typing import Generator, List
from dask.diagnostics import ProgressBar
import logging
import pyarrow.compute as pc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

### === DASK IMPLEMENTATION === ###
def load_corpus_dask(corpus_path: str) -> Generator[str, None, None]:
    """Efficiently load and process a corpus in parallel using Dask."""
    start_time = time.time()
    
    ddf = dd.read_parquet(corpus_path, engine="pyarrow")

    # Convert partitions to delayed objects
    delayed_partitions = ddf.to_delayed()
    
    with ProgressBar():
        # Process each partition lazily
        for partition in delayed_partitions:
            df = partition.compute()
            yield from (df['title'] + ' ' + df['body']).tolist()

    end_time = time.time()
    print(f"Dask Implementation Completed in {end_time - start_time:.2f} seconds")

### === RAY IMPLEMENTATION === ###
@ray.remote
def process_subtable(arrow_subtable: pa.Table) -> pl.DataFrame:
    """
    Process a sub-table of rows (Arrow format), using Polars for vectorized operations.
    Returns a Polars DataFrame (which Ray can serialize).
    """
    df = pl.from_arrow(arrow_subtable)
    # Example: create a new column 'combined' by joining title + body
    df = df.with_columns(
        (pl.col("title") + pl.lit(" ") + pl.col("body")).alias("combined")
    )
    # Potentially do more vectorized operations...
    return df[["combined"]]  # Return a smaller subset

def load_corpus_parallel(corpus_path: str, chunk_size: int = 10_000) -> Generator[str, None, None]:
    """
    Efficiently load and process a Parquet file in parallel using Ray.
    - Reads each row group in Arrow format.
    - Uses zero-copy slicing (Arrow's .slice) to split large row groups into chunks.
    - Passes the sliced Arrow tables to remote tasks without converting to Python lists.
    - Returns processed strings from the resulting Polars DataFrame.
    """
    start_time = time.time()
    parquet_file = pq.ParquetFile(corpus_path)
    total_row_groups = parquet_file.num_row_groups

    logger.info("Generating sub-table futures...")
    futures = []

    # Read each row group in Arrow format, then slice it into smaller chunks
    for rg_idx in range(total_row_groups):
        arrow_table = parquet_file.read_row_group(rg_idx)
        num_rows = arrow_table.num_rows

        # Slicing the Arrow table to create sub-tables of size `chunk_size`
        start = 0
        while start < num_rows:
            length = min(chunk_size, num_rows - start)
            # Zero-copy slice: does not reallocate or copy underlying data buffers
            sub_table = arrow_table.slice(offset=start, length=length)
            futures.append(process_subtable.remote(sub_table))
            start += length

    logger.info(f"Generated {len(futures)} futures. Fetching results...")

    # Fetch results in manageable chunks (say 50) to avoid memory pressure
    while futures:
        ready, futures = ray.wait(futures, num_returns=min(50, len(futures)))

        for finished_ref in ready:
            try:
                # Each returned object is a Polars DataFrame with column "combined"
                result_df = ray.get(finished_ref)
                # Yield each string in the "combined" column
                yield from result_df["combined"].to_list()
            except Exception as e:
                logger.error(f"Error processing sub-table: {e}")

    logger.info(f"Ray processing completed in {time.time() - start_time:.2f}s")

### === ARGPARSE HANDLING === ###
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Choose execution method for corpus loading")
    parser.add_argument(
        "--method", choices=["ray", "dask"], required=True, 
        help="Select method to run: 'ray' for Ray implementation, 'dask' for Dask implementation"
    )

    args = parser.parse_args()
    corpus_path = "../data/corpus/dataset.parquet"

    if args.method == "ray":
        print("\n🚀 Running Ray Implementation...")
        ray.init(ignore_reinit_error=True)
        start_time = time.time()
        for _ in load_corpus_parallel(corpus_path):
            pass  # Consume generator
        print(f"⏳ Ray Execution Time: {time.time() - start_time:.2f} sec\n")
        ray.shutdown()

    elif args.method == "dask":
        print("\n🚀 Running Dask Implementation...")
        start_time = time.time()
        for _ in load_corpus_dask(corpus_path):
            pass  # Consume generator
        print(f"⏳ Dask Execution Time: {time.time() - start_time:.2f} sec\n")

import csv
import json
import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from typing import List

# Increase CSV field size limit
csv.field_size_limit(2**30)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "corpus", "msmarco-docs.tsv")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "msmarco-docs.json")
BATCH_SIZE = 10000

def process_batch(rows: List[List[str]]) -> List[str]:
    """Process a batch of rows and return JSON strings."""
    return [
        json.dumps({
            "docid": row[0],
            "url": row[1],
            "title": row[2],
            "body": row[3]
        })
        for row in rows
        if len(row) == 4
    ]

def preprocess_corpus(input_file: str, output_file: str):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with ProcessPoolExecutor() as executor:
        with open(input_file, 'r', encoding='utf8') as infile, \
             open(output_file, 'w', encoding='utf8', buffering=1024*1024) as outfile:
            
            tsv_reader = csv.reader(infile, delimiter='\t')
            batch = []
            futures = []
            
            with tqdm(total=None, desc="Processing documents", unit=" docs") as pbar:
                for row in tsv_reader:
                    batch.append(row)
                    pbar.update(1)
                    
                    if len(batch) >= BATCH_SIZE:
                        future = executor.submit(list, process_batch(batch))
                        futures.append(future)
                        batch = []
                        
                        # Write completed batches
                        while futures and futures[0].done():
                            results = futures.pop(0).result()
                            outfile.write('\n'.join(results) + '\n')
                
                # Process remaining rows
                if batch:
                    future = executor.submit(list, process_batch(batch))
                    futures.append(future)
                
                # Wait for and write remaining results
                for future in futures:
                    results = future.result()
                    outfile.write('\n'.join(results) + '\n')

if __name__ == "__main__":
    preprocess_corpus(INPUT_FILE, OUTPUT_FILE)
    print(f"Corpus processed and saved to {OUTPUT_FILE}")

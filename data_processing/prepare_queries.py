import csv
import json
import os
from tqdm import tqdm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "train", "queries.doctrain.tsv")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "queries.json")

def extract_queries(input_file, output_file):
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    queries = {}
    with open(input_file, 'r', encoding='utf8') as f:
        total_lines = sum(1 for _ in f)
    
    with open(input_file, 'r', encoding='utf8') as infile:
        reader = csv.reader(infile, delimiter='\t')
        for row in tqdm(reader, total=total_lines, desc="Extracting queries"):
            qid, query = row
            queries[qid] = query

    with open(output_file, 'w', encoding='utf8') as outfile:
        json.dump(queries, outfile, indent=4)

if __name__ == "__main__":
    extract_queries(INPUT_FILE, OUTPUT_FILE)

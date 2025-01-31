from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Search settings
    page_size: int = 10
    search_result_limit: int = 100
    
    # Cache settings
    max_cache_queries: int = 5
    cache_ttl: int = 3600
    
    # Elasticsearch settings
    elasticsearch_url: str = "http://elasticsearch:9200"  # For local development
    elasticsearch_timeout: int = 30
    elasticsearch_retry_count: int = 3
    
    # Redis settings
    redis_url: str = "redis://redis:6379"
    
    # Elasticsearch detailed settings
    es_username: Optional[str] = None
    es_password: Optional[str] = None
    es_verify_certs: bool = False
    batch_size: int = 1000
    max_retries: int = 3
    retry_interval: int = 5
    max_concurrent_batches: int = 5
    es_mappings: Dict[str, Any] = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "30s",
            "translog": {
                "durability": "async"
            },
            "analysis": {
                "char_filter": {
					"remove_standalone_slash": {
						"type": "pattern_replace",
						"pattern": r"(^/|/$)",
						"replacement": ""  # Remove standalone `/`
					}
				},
				"tokenizer": {
					"custom_slash_tokenizer": {
						"type": "pattern",
						"pattern": r"(?<!\w)/|/(?!\w)",  # Split only on `/` not surrounded by letters
						"group": -1
					}
				},
                "analyzer": {
                    "custom_baseline_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",    # Convert text to lowercase
                            "asciifolding", # Normalize special characters (e.g., é -> e)
                            "stop"          # Remove common stop words
                        ]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "docid": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "custom_baseline_analyzer",  # Use the custom analyzer
                },
                "body": {
                    "type": "text",
                    "analyzer": "custom_baseline_analyzer"  # Use the custom analyzer
                }
            }
        }
    }
    
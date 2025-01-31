"""
Query parsing and cleaning step.
Handles basic text processing and structure analysis of search queries.
"""

import re
from typing import List, Tuple, Set, Dict
from dataclasses import dataclass
from core.pipeline.base import PipelineStep
from core.pipeline.context import SearchContext
import logging
import unicodedata
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ParsedQuery:
    """
    Structured representation of a parsed search query.
    
    Attributes:
        original: The original unmodified query
        cleaned: Basic cleaned version (lowercase, normalized spaces)
        exact_phrases: List of phrases that should be matched exactly (from quotes)
        keywords: Individual keywords after removing exact phrases and cleaning
        detected_phrases: List of phrases detected in the query
    """
    original: str
    cleaned: str
    exact_phrases: List[str]
    keywords: List[str]
    detected_phrases: List[str] = None

class QueryParser(PipelineStep):
    """
    Pipeline step for parsing and cleaning search queries.
    Handles basic text cleaning, phrase detection, and keyword extraction.
    """
    
    # Common English stop words to handle specially in phrase contexts
    STOP_WORDS: Set[str] = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
        'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
        'that', 'the', 'to', 'was', 'were', 'will', 'with'
    }

    # Common English contractions to handle specially in phrase contexts
    CONTRACTIONS: Dict[str, str] = {
        r"\bcan't\b": "cannot", r"\bwon't\b": "will not", r"\bit's\b": "it is",
        r"\bI'm\b": "I am", r"\byou're\b": "you are", r"\bthey're\b": "they are",
        r"\bhe's\b": "he is", r"\bshe's\b": "she is", r"\bwe're\b": "we are",
        r"\bdoesn't\b": "does not", r"\bisn't\b": "is not"
    }

    def __init__(self):
        self.exact_phrase_pattern = re.compile(r'"([^"]*)"')
        self.key_phrases = self._load_key_phrases()
    
    def _load_key_phrases(self) -> List[str]:
        """Load precomputed key phrases from file"""
        try:
            path = Path("data/processed/key_phrases.json")
            if not path.exists():
                logger.warning("Key phrases file not found, using empty list")
                return []
                
            with open(path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load key phrases: {e}")
            return []

    def _extract_exact_phrases(self, query: str) -> Tuple[List[str], str]:
        """
        Extract quoted phrases from query and return them along with remaining text.
        
        Args:
            query: Raw query string
            
        Returns:
            Tuple of (list of exact phrases, remaining query text)
        """
        phrases = []
        remaining_text = query
        
        # Find all quoted phrases
        matches = self.exact_phrase_pattern.findall(query)
        if matches:
            phrases = [phrase.strip().lower() for phrase in matches if phrase.strip()]
            # Remove quoted sections from query
            remaining_text = self.exact_phrase_pattern.sub('', query)
            
        logger.debug(f"Extracted phrases: {phrases}")
        return phrases, remaining_text
    
    def _clean_text(self, text: str) -> str:
        """
        Apply basic text cleaning operations.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase
        cleaned = text.lower()
        
        # Remove diacritical marks
        cleaned = ''.join(
            c for c in unicodedata.normalize('NFKD', text.lower())
            if unicodedata.category(c) != 'Mn'
        )
        
        # Replace common contractions
        for pattern, replacement in self.CONTRACTIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Remove special characters except quotes
        cleaned = re.sub(r'[^\w\s":,.!?]', ' ', cleaned)
        
        # Normalize spaces again after special char removal
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text, handling stop words appropriately.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Split into words
        words = text.split()
        
        # Filter out empty strings and handle stop words
        keywords = []
        for word in words:
            word = word.strip()
            if not word:
                continue
                
            # Keep stop words only in exact phrases
            if word in self.STOP_WORDS:
                continue
                
            keywords.append(word)
            
        return keywords
    
    def _detect_common_phrases(self, text: str) -> List[str]:
        """
        Detect common phrases from precomputed list in the query text.
        Prioritizes longer phrases first.
        """
        detected = []
        remaining_text = text.lower()
        
        # Check phrases in descending order of length
        for phrase in sorted(self.key_phrases, key=len, reverse=True):
            if phrase in remaining_text:
                detected.append(phrase)
                # Remove found phrase to prevent substring matches
                remaining_text = remaining_text.replace(phrase, "")
                
        return detected

    async def process(self, context: SearchContext) -> SearchContext:
        """
        Process the search query through parsing and cleaning steps.
        
        Args:
            context: Search context containing original query
            
        Returns:
            Updated context with parsed query
        """
        if not context.original_query:
            logger.warning("Received empty query")
            context.parsed_query = ""
            return context
            
        # Clean the original query
        cleaned_query = self._clean_text(context.original_query)
        
        # Extract exact phrases
        exact_phrases, remaining_text = self._extract_exact_phrases(cleaned_query)
        
        # Extract keywords from remaining text
        keywords = self._extract_keywords(remaining_text)
        
        # Detect common phrases from corpus
        detected_phrases = self._detect_common_phrases(cleaned_query)
        
        # Create structured parsed query
        parsed_query = ParsedQuery(
            original=context.original_query,
            cleaned=cleaned_query,
            exact_phrases=exact_phrases,
            keywords=keywords,
            detected_phrases=detected_phrases
        )
        
        # Log parsing results
        logger.info(
            f"Parsed query: original='{context.original_query}' -> "
            f"cleaned='{cleaned_query}', "
            f"phrases={exact_phrases}, "
            f"keywords={keywords}, "
            f"detected_phrases={detected_phrases}"
        )
        
        # Update context
        context.parsed_query = parsed_query
        
        return context 
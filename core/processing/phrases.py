"""
Optimized TF-IDF phrase extraction using sparse matrices and efficient tokenization.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class TFIDFPhraseExtractor:
    def __init__(self, ngram_range=(2, 3), max_features=5000):
        self.vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            stop_words='english',
            token_pattern=r'(?u)\b[\w-]{2,}\b',  # More efficient token pattern
            min_df=5,          # Ignore rare terms
            max_df=0.95,       # Ignore overly common terms
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True,  # Use 1 + log(tf)
            n_jobs=-1           # Use all CPU cores
        )

    def extract_key_phrases(self, documents: list[str], top_n: int = 1000) -> list[str]:
        """
        Optimized phrase extraction using sparse matrix operations.
        
        Args:
            documents: List of document strings (keep documents separate for proper IDF)
            top_n: Number of top phrases to return
            
        Returns:
            List of key phrases ordered by TF-IDF score
        """
        # Fit and transform using sparse matrices
        tfidf_matrix = self.vectorizer.fit_transform(documents)
        
        # Sum TF-IDF scores across documents using sparse matrix
        doc_scores = tfidf_matrix.sum(axis=0).A1  # More efficient conversion to 1D array
        
        # Get feature names and sort using numpy for better performance
        feature_names = np.array(self.vectorizer.get_feature_names_out())
        sorted_indices = np.argsort(doc_scores)[::-1][:top_n]
        
        return feature_names[sorted_indices].tolist() 
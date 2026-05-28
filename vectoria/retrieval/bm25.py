import numpy as np
from typing import List
from rank_bm25 import BM25Okapi
from vectoria.models import Chunk

class BM25Retriever:
    """
    Lexical matching module using BM25.
    Used alongside dense embeddings for Hybrid Search.
    """
    def __init__(self):
        self.bm25 = None
        self.chunks = []
        
    def fit(self, chunks: List[Chunk]):
        self.chunks = chunks
        tokenized_corpus = [self._tokenize(chunk.text) for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple lightweight tokenization."""
        return text.lower().replace(".", " ").replace(",", " ").split()
        
    def get_scores(self, query: str) -> np.ndarray:
        if not self.bm25:
            raise RuntimeError("BM25 not fitted. Call fit() first.")
        tokenized_query = self._tokenize(query)
        return self.bm25.get_scores(tokenized_query)

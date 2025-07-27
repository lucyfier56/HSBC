import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import os

# Simple in-memory vector database for demo
class SimpleVectorDB:
    def __init__(self):
        self.documents = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.vectors = None
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load knowledge base from file"""
        kb_path = "data/knowledge_base.txt"
        if os.path.exists(kb_path):
            with open(kb_path, 'r') as f:
                content = f.read()
                # Split into chunks
                chunks = content.split('\n\n')
                self.documents = [chunk.strip() for chunk in chunks if chunk.strip()]
        else:
            # Default knowledge base
            self.documents = [
                "Our personal loan interest rates start from 5.2% APR. The exact rate depends on your credit score and income.",
                "You can apply for a personal loan online through our banking app or website. The process takes 2-3 business days.",
                "Credit card applications are processed within 7-10 business days. You need a minimum income of $25,000 annually.",
                "Our savings account offers 2.1% annual interest rate with no minimum balance requirement.",
                "For checking accounts, we offer free checking with no monthly maintenance fees when you maintain a $500 minimum balance."
            ]
        
        if self.documents:
            self.vectors = self.vectorizer.fit_transform(self.documents)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant documents"""
        if not self.documents or self.vectors is None:
            return []
        
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.vectors).flatten()
        
        # Get top-k most similar documents
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold for relevance
                results.append({
                    "content": self.documents[idx],
                    "score": float(similarities[idx])
                })
        
        return results

# Global instance
_vector_db = SimpleVectorDB()

def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict]:
    """Search the knowledge base"""
    return _vector_db.search(query, top_k)

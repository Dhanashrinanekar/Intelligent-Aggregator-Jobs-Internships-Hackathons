
"""TF-IDF Vectorization Service"""
from sklearn.feature_extraction.text import TfidfVectorizer
import json
import numpy as np
from typing import List, Tuple

class VectorizerService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.is_fitted = False
    
    def prepare_text(self, role: str = "", skills: str = "", company: str = "") -> str:
        """Combine job/resume fields into single text"""
        parts = []
        if role:
            parts.append(role)
        if skills:
            parts.append(skills)
        if company:
            parts.append(company)
        return " ".join(parts)
    
    def fit_transform_corpus(self, texts: List[str]) -> np.ndarray:
        """Fit vectorizer and transform texts"""
        vectors = self.vectorizer.fit_transform(texts)
        self.is_fitted = True
        return vectors.toarray()
    
    def transform_text(self, text: str) -> np.ndarray:
        """Transform single text to vector"""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted first")
        return self.vectorizer.transform([text]).toarray()[0]
    
    def vector_to_json(self, vector: np.ndarray) -> str:
        """Convert numpy array to JSON string"""
        return json.dumps(vector.tolist())
    
    def json_to_vector(self, json_str: str) -> np.ndarray:
        """Convert JSON string to numpy array"""
        return np.array(json.loads(json_str))
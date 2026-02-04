import openai
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

from ai_service.config import config


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        self.use_local = config.use_local_embedding
        
        if self.use_local:
            # TODO: Configure local embedding model
            # Using BGE model for Chinese text
            self.model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
            self.dimension = 1024
            print("Using local BGE embedding model")
        else:
            # TODO: Configure OpenAI embedding model
            self.model_name = config.embedding_model
            self.dimension = 1536 if "3-small" in self.model_name else 1536
            openai.api_key = config.openai_api_key
            print(f"Using OpenAI embedding model: {self.model_name}")
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode text to embedding vector(s)"""
        if self.use_local:
            return self._encode_local(text)
        else:
            return self._encode_openai(text)
    
    def _encode_local(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode using local model"""
        embeddings = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
    
    def _encode_openai(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode using OpenAI API"""
        if isinstance(text, str):
            text = [text]
        
        response = openai.embeddings.create(
            model=self.model_name,
            input=text
        )
        
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings[0] if len(text) == 1 else embeddings)
    
    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Batch encode texts"""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.encode(batch)
            if len(batch) == 1:
                embeddings.append(batch_embeddings)
            else:
                embeddings.extend(batch_embeddings)
        return embeddings

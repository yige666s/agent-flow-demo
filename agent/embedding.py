import openai
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

from config import config


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        self.use_local = config.use_local_embedding
        
        if self.use_local:
            # Configure local embedding model
            # Using BGE model for Chinese text
            self.model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
            self.dimension = 1024
            print("Using local BGE embedding model")
        else:
            # Configure API-based embedding model
            self.model_name = config.embedding_model
            
            # Determine API Key and Base URL based on provider
            api_key = config.embedding_api_key
            base_url = config.embedding_api_base
            
            if config.embedding_provider == "zhipu":
                api_key = api_key or config.zhipu_api_key
                base_url = base_url or "https://open.bigmodel.cn/api/paas/v4/"
                self.dimension = 1024 # Zhipu usually 1024 for embedding-2, but can be variable. 
            elif config.embedding_provider == "qwen":
                api_key = api_key or config.dashscope_api_key
                base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                self.dimension = 1536 # Qwen-text-embedding-v1 is 1536, v2 is 1536
            elif config.embedding_provider == "openai":
                api_key = api_key or config.openai_api_key
                # dim defaults to 1536 usually
                self.dimension = 1536
            
            # Fallback/Generic
            if not api_key:
                # Try generic LLM key if embedding specific one is missing
                api_key = config.llm_api_key

            if not api_key:
                print("Warning: No API Key found for embedding service!")

            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None
            )
            print(f"Using {config.embedding_provider} embedding model: {self.model_name}")
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode text to embedding vector(s)"""
        if self.use_local:
            return self._encode_local(text)
        else:
            return self._encode_api(text)
    
    def _encode_local(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode using local model"""
        embeddings = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
    
    def _encode_api(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode using API"""
        if isinstance(text, str):
            text = [text]
        
        # Ensure text is not empty list
        if not text:
            return np.array([])
            
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings[0] if len(text) == 1 else embeddings)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector on error to avoid crash
            return np.zeros(self.dimension) if isinstance(text, str) or len(text)==1 else np.zeros((len(text), self.dimension))

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

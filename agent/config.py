import os

from typing import Any, Dict
import yaml
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # LLM Configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        self.llm_api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.llm_api_base = os.getenv("LLM_API_BASE", "")
        
        # Backward compatibility for OpenAI specific vars if set and generic ones aren't
        if not self.llm_api_key and self.llm_provider == 'openai':
             self.llm_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Specific provider configs (optional)
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.zhipu_api_key = os.getenv("ZHIPU_API_KEY", "")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Configure embedding model
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY", "")
        self.embedding_api_base = os.getenv("EMBEDDING_API_BASE", "")
        self.use_local_embedding = os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true"
        
        # TODO: Configure Milvus connection
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        
        # gRPC server config
        self.grpc_port = int(os.getenv("GRPC_PORT", "50051"))
        
    @classmethod
    def load_from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file"""
        config = cls()
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                # TODO: Override with file config
                if 'openai' in data:
                    config.openai_api_key = data['openai'].get('api_key', config.openai_api_key)
                    config.openai_model = data['openai'].get('model', config.openai_model)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
        return config

# Global config instance
config = Config()

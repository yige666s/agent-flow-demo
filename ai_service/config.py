import os
from typing import Any, Dict
import yaml

class Config:
    def __init__(self):
        # TODO: Load from environment variables or config file
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        
        # TODO: Configure embedding model
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
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

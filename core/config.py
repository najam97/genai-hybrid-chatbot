"""
Configuration and environment settings for the Hybrid Chatbot.
Supports both OpenAI and Azure OpenAI APIs.
"""

import os
from typing import Optional, Literal


class Config:
    """Centralized configuration management with dependency injection support."""
    
    # LLM Provider: 'openai' or 'azure'
    LLM_PROVIDER: Literal['openai', 'azure'] = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    AZURE_API_VERSION: str = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    
    # Database Configuration
    DB_PATH: str = os.getenv("DB_PATH", "data/mock_db.sqlite")
    DB_READ_ONLY: bool = True  # Enforce read-only execution
    
    # Vector Database Configuration (placeholder for future integration)
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "mock")  # 'faiss', 'pinecone', 'mock'
    VECTOR_DB_PATH: Optional[str] = os.getenv("VECTOR_DB_PATH", None)
    
    # Routing Configuration
    ROUTING_TEMPERATURE: float = 0.0  # Deterministic routing
    ROUTING_CONFIDENCE_THRESHOLD: float = 0.5
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> None:
        """Validate critical configuration parameters."""
        if cls.LLM_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError(
                    "OpenAI provider selected but OPENAI_API_KEY is not set.\n"
                    "Please set: export OPENAI_API_KEY=sk-your-key"
                )
        elif cls.LLM_PROVIDER == "azure":
            if not cls.AZURE_OPENAI_API_KEY:
                raise ValueError(
                    "Azure provider selected but AZURE_OPENAI_API_KEY is not set.\n"
                    "Please set: export AZURE_OPENAI_API_KEY=your-key"
                )
            if not cls.AZURE_OPENAI_ENDPOINT:
                raise ValueError(
                    "Azure provider selected but AZURE_OPENAI_ENDPOINT is not set.\n"
                    "Please set: export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
                )
            if not cls.AZURE_OPENAI_DEPLOYMENT:
                raise ValueError(
                    "Azure provider selected but AZURE_OPENAI_DEPLOYMENT is not set.\n"
                    "Please set: export AZURE_OPENAI_DEPLOYMENT=your-deployment-name"
                )
        else:
            raise ValueError(f"Invalid LLM_PROVIDER: {cls.LLM_PROVIDER}. Must be 'openai' or 'azure'")
        
        if not cls.DB_PATH or not os.path.exists(cls.DB_PATH):
            raise FileNotFoundError(f"Database not found at {cls.DB_PATH}. Run 'python scripts/init_db.py' first.")
    
    @classmethod
    def to_dict(cls) -> dict:
        """Return configuration as dictionary (useful for logging)."""
        config_dict = {
            "llm_provider": cls.LLM_PROVIDER,
            "db_path": cls.DB_PATH,
            "db_read_only": cls.DB_READ_ONLY,
            "vector_db_type": cls.VECTOR_DB_TYPE,
            "routing_temperature": cls.ROUTING_TEMPERATURE,
        }
        
        if cls.LLM_PROVIDER == "openai":
            config_dict["openai_model"] = cls.OPENAI_MODEL
        elif cls.LLM_PROVIDER == "azure":
            config_dict["azure_deployment"] = cls.AZURE_OPENAI_DEPLOYMENT
            config_dict["azure_endpoint"] = cls.AZURE_OPENAI_ENDPOINT
        
        return config_dict

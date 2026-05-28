from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""
    
    # LLM Provider
    vectoria_llm_api_key: str = ""
    vectoria_model_name: str = "gemini-2.5-pro"
    
    # Retrieval Settings
    vectoria_top_k_default: int = 5
    vectoria_max_context_tokens: int = 4000
    
    # Server & Security
    vectoria_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins_list(self) -> List[str]:
        if self.vectoria_allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.vectoria_allowed_origins.split(",") if origin.strip()]

settings = Settings()

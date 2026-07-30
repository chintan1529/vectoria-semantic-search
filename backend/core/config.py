from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings, loaded strictly from environment variables or .env file.
    
    Settings are immutable after startup.
    """
    
    # Provider Intent Selection
    vectoria_chat_provider: str = Field("gemini", validation_alias="VECTORIA_CHAT_PROVIDER")
    vectoria_research_provider: str = Field("gemini", validation_alias="VECTORIA_RESEARCH_PROVIDER")
    vectoria_fallback_provider: Optional[str] = Field("huggingface", validation_alias="VECTORIA_FALLBACK_PROVIDER")

    # Gemini Namespace
    vectoria_gemini_api_key: Optional[str] = Field(None, validation_alias="VECTORIA_GEMINI_API_KEY")
    vectoria_gemini_model: str = Field("gemini-2.5-flash", validation_alias="VECTORIA_GEMINI_MODEL")

    # Hugging Face Namespace
    vectoria_hf_api_key: Optional[str] = Field(None, validation_alias="VECTORIA_HF_API_KEY")
    vectoria_hf_model: str = Field("microsoft/Phi-3-mini-4k-instruct", validation_alias="VECTORIA_HF_MODEL")
    vectoria_hf_research_model: str = Field("Qwen/Qwen2.5-7B-Instruct", validation_alias="VECTORIA_HF_RESEARCH_MODEL")
    vectoria_hf_embed_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", validation_alias="VECTORIA_HF_EMBED_MODEL")
    vectoria_hf_rerank_model: str = Field("cross-encoder/ms-marco-MiniLM-L-6-v2", validation_alias="VECTORIA_HF_RERANK_MODEL")

    # OpenAI Namespace
    vectoria_openai_api_key: Optional[str] = Field(None, validation_alias="VECTORIA_OPENAI_API_KEY")
    vectoria_openai_model: str = Field("gpt-4o-mini", validation_alias="VECTORIA_OPENAI_MODEL")

    # Anthropic Namespace
    vectoria_anthropic_api_key: Optional[str] = Field(None, validation_alias="VECTORIA_ANTHROPIC_API_KEY")
    vectoria_anthropic_model: str = Field("claude-3-5-sonnet-20241022", validation_alias="VECTORIA_ANTHROPIC_MODEL")

    # Groq Namespace
    vectoria_groq_api_key: Optional[str] = Field(None, validation_alias="VECTORIA_GROQ_API_KEY")
    vectoria_groq_model: str = Field("llama-3.3-70b-versatile", validation_alias="VECTORIA_GROQ_MODEL")

    # Ollama Namespace
    vectoria_ollama_url: str = Field("http://localhost:11434", validation_alias="VECTORIA_OLLAMA_URL")
    vectoria_ollama_model: str = Field("qwen2.5:3b-instruct", validation_alias="VECTORIA_OLLAMA_MODEL")
    vectoria_ollama_research_model: str = Field("qwen2.5:7b-instruct", validation_alias="VECTORIA_OLLAMA_RESEARCH_MODEL")
    
    # Retrieval Settings
    vectoria_top_k_default: int = Field(5, validation_alias="VECTORIA_TOP_K_DEFAULT")
    vectoria_max_context_tokens: int = Field(4000, validation_alias="VECTORIA_MAX_CONTEXT_TOKENS")
    
    # Server & Security
    vectoria_allowed_origins: str = Field("http://localhost:3000,http://127.0.0.1:3000", validation_alias="VECTORIA_ALLOWED_ORIGINS")
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore",
        frozen=True  # Immutability enforcement (Phase 8)
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        if self.vectoria_allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.vectoria_allowed_origins.split(",") if origin.strip()]

settings = Settings()

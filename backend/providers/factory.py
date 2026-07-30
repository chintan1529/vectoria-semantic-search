from typing import List, Optional
from backend.core.config import settings
from backend.core.logging import logger
from backend.core.exceptions import ConfigurationError
from backend.providers.base_provider import BaseLLMProvider
from backend.providers.failover import FailoverProviderWrapper

class ProviderFactory:
    """
    Pure dependency injector for LLM Providers (Phase 5).
    
    Guarantees:
      - Zero business logic / fallback decisions
      - Zero hardcoded model names
      - Strictly reads values from immutable `settings`
      - Instantiates and returns initialized provider instances
    """

    @staticmethod
    def _create_provider_instance(name: str, is_research: bool = False) -> Optional[BaseLLMProvider]:
        name = name.strip().lower()
        try:
            if name == "gemini":
                from backend.providers.gemini_provider import GeminiProvider
                api_key = settings.vectoria_gemini_api_key
                if not api_key:
                    logger.error("Gemini requested but VECTORIA_GEMINI_API_KEY is missing.")
                    return None
                return GeminiProvider(api_key=api_key, model_name=settings.vectoria_gemini_model)

            elif name == "huggingface":
                from backend.providers.huggingface_provider import HuggingFaceProvider
                api_key = settings.vectoria_hf_api_key
                if not api_key:
                    logger.error("HuggingFace requested but VECTORIA_HF_API_KEY is missing.")
                    return None
                model = settings.vectoria_hf_research_model if is_research else settings.vectoria_hf_model
                return HuggingFaceProvider(api_key=api_key, model_name=model)

            elif name == "ollama":
                from backend.providers.ollama_provider import OllamaProvider
                model = settings.vectoria_ollama_research_model if is_research else settings.vectoria_ollama_model
                return OllamaProvider(base_url=settings.vectoria_ollama_url, model_name=model)

            elif name == "openai":
                from backend.providers.openai_provider import OpenAIProvider
                api_key = settings.vectoria_openai_api_key
                if not api_key:
                    logger.error("OpenAI requested but VECTORIA_OPENAI_API_KEY is missing.")
                    return None
                return OpenAIProvider(api_key=api_key, model_name=settings.vectoria_openai_model)

            elif name == "anthropic":
                from backend.providers.anthropic_provider import AnthropicProvider
                api_key = settings.vectoria_anthropic_api_key
                if not api_key:
                    logger.error("Anthropic requested but VECTORIA_ANTHROPIC_API_KEY is missing.")
                    return None
                return AnthropicProvider(api_key=api_key, model_name=settings.vectoria_anthropic_model)

            elif name == "groq":
                from backend.providers.groq_provider import GroqProvider
                api_key = settings.vectoria_groq_api_key
                if not api_key:
                    logger.error("Groq requested but VECTORIA_GROQ_API_KEY is missing.")
                    return None
                return GroqProvider(api_key=api_key, model_name=settings.vectoria_groq_model)

            else:
                logger.warning(f"Unknown provider: {name}")
                return None
        except Exception as e:
            logger.error(f"Failed to instantiate provider {name}: {e}")
            return None

    @classmethod
    def create_chat_provider(cls) -> BaseLLMProvider:
        """Instantiates chat provider based strictly on configured intent."""
        chat_prov = settings.vectoria_chat_provider.strip()
        fallback_prov = settings.vectoria_fallback_provider.strip() if settings.vectoria_fallback_provider else None

        providers = []
        primary = cls._create_provider_instance(chat_prov, is_research=False)
        if primary:
            providers.append(primary)

        if fallback_prov and fallback_prov != chat_prov:
            fallback = cls._create_provider_instance(fallback_prov, is_research=False)
            if fallback:
                providers.append(fallback)

        if not providers:
            raise ConfigurationError(f"Failed to initialize primary chat provider '{chat_prov}'. Startup aborted.")

        return FailoverProviderWrapper(providers=providers, max_retries_per_provider=2)

    @classmethod
    def create_research_provider(cls) -> BaseLLMProvider:
        """Instantiates research provider based strictly on configured intent."""
        research_prov = settings.vectoria_research_provider.strip()
        fallback_prov = settings.vectoria_fallback_provider.strip() if settings.vectoria_fallback_provider else None

        providers = []
        primary = cls._create_provider_instance(research_prov, is_research=True)
        if primary:
            providers.append(primary)

        if fallback_prov and fallback_prov != research_prov:
            fallback = cls._create_provider_instance(fallback_prov, is_research=True)
            if fallback:
                providers.append(fallback)

        if not providers:
            logger.warning(f"Research provider '{research_prov}' unavailable. Research mode degraded.")
            return None

        return FailoverProviderWrapper(providers=providers, max_retries_per_provider=2)

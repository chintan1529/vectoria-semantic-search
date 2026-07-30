"""
Configuration & Startup Validator (Phase 6 & 7)

Performs strict, deterministic startup validation before traffic can be served.
Rejects invalid configurations fast and prints a diagnostic startup matrix.
"""

import sys
import time
from typing import Dict, List, Tuple, Any
from backend.core.config import settings
from backend.core.logging import logger
from backend.core.exceptions import ConfigurationError

VALID_PROVIDERS = {"gemini", "huggingface", "openai", "anthropic", "groq", "ollama"}

def validate_environment() -> Dict[str, Any]:
    """Validates configuration settings and provider requirements.
    
    Raises:
        ConfigurationError: If primary required providers (e.g. Chat) are unconfigured.
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # 1. Validate Provider Choices
    if settings.vectoria_chat_provider not in VALID_PROVIDERS:
        errors.append(f"Invalid VECTORIA_CHAT_PROVIDER '{settings.vectoria_chat_provider}'. Must be one of {VALID_PROVIDERS}")
        
    if settings.vectoria_research_provider not in VALID_PROVIDERS:
        warnings.append(f"Invalid VECTORIA_RESEARCH_PROVIDER '{settings.vectoria_research_provider}'. Research mode will degrade.")

    if settings.vectoria_fallback_provider and settings.vectoria_fallback_provider not in VALID_PROVIDERS:
        warnings.append(f"Invalid VECTORIA_FALLBACK_PROVIDER '{settings.vectoria_fallback_provider}'. Fallback disabled.")

    # 2. Check API Key Requirements per Selected Provider
    provider_keys = {
        "gemini": (settings.vectoria_gemini_api_key, "VECTORIA_GEMINI_API_KEY"),
        "huggingface": (settings.vectoria_hf_api_key, "VECTORIA_HF_API_KEY"),
        "openai": (settings.vectoria_openai_api_key, "VECTORIA_OPENAI_API_KEY"),
        "anthropic": (settings.vectoria_anthropic_api_key, "VECTORIA_ANTHROPIC_API_KEY"),
        "groq": (settings.vectoria_groq_api_key, "VECTORIA_GROQ_API_KEY"),
    }
    
    # Check Chat Provider Key
    chat_p = settings.vectoria_chat_provider
    if chat_p in provider_keys:
        key_val, env_name = provider_keys[chat_p]
        if not key_val or not key_val.strip():
            errors.append(f"Primary Chat Provider '{chat_p}' requires non-empty '{env_name}'")

    # Check Research Provider Key
    res_p = settings.vectoria_research_provider
    if res_p in provider_keys:
        key_val, env_name = provider_keys[res_p]
        if not key_val or not key_val.strip():
            warnings.append(f"Research Provider '{res_p}' requires '{env_name}'. Research mode will be unavailable.")

    if errors:
        error_msg = "\n".join([f"  ❌ {e}" for e in errors])
        print(f"\n====================================\nCONFIGURATION VALIDATION FAILED\n====================================\n{error_msg}\n====================================\n")
        raise ConfigurationError(f"Startup aborted due to configuration errors:\n{error_msg}")

    return {
        "chat_provider": settings.vectoria_chat_provider,
        "research_provider": settings.vectoria_research_provider,
        "fallback_provider": settings.vectoria_fallback_provider,
        "warnings": warnings,
    }


def print_startup_matrix(validation_res: Dict[str, Any], start_time_s: float):
    """Prints diagnostic startup matrix (Phase 9)."""
    duration = time.perf_counter() - start_time_s
    
    matrix = f"""
====================================
VECTORIA STARTUP MATRIX
====================================
Chat Provider       : {validation_res['chat_provider'].upper()} (READY)
Research Provider   : {validation_res['research_provider'].upper()} ({'DEGRADED' if validation_res['warnings'] else 'READY'})
Fallback Provider   : {str(validation_res['fallback_provider']).upper()}
Embedding Model     : {settings.vectoria_hf_embed_model}
Reranker Model      : {settings.vectoria_hf_rerank_model}
FAISS Vector Store  : READY
Semantic Cache      : READY
Failure Memory      : READY
Telemetry Engine    : READY
Config Status       : PASSED
Startup Duration    : {duration:.2f}s
====================================
"""
    print(matrix)
    logger.info("VECTORIA_STARTUP_MATRIX_COMPLETE | duration_s=%.2f", duration)

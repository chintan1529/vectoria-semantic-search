# Configuration Audit Report

This audit documents all instances of legacy, ambiguous, or deprecated environment variables prior to architectural refactoring.

## Legacy Variables Audited
- `VECTORIA_LLM_API_KEY`
- `VECTORIA_MODEL_NAME`
- `VECTORIA_LLM_PROVIDER`

## Audit Matrix

| File | Line | Purpose | Action / Replacement |
|---|---|---|---|
| `backend/core/config.py` | 9 | `vectoria_llm_provider` setting field | ❌ Remove completely. Replaced by `VECTORIA_CHAT_PROVIDER`, `VECTORIA_RESEARCH_PROVIDER`, `VECTORIA_FALLBACK_PROVIDER`. |
| `backend/core/config.py` | 15 | `vectoria_llm_api_key` setting field | ❌ Remove completely. Replaced by provider-specific `VECTORIA_OPENAI_API_KEY`, `VECTORIA_GEMINI_API_KEY`, etc. |
| `backend/core/config.py` | 16 | `vectoria_model_name` setting field | ❌ Remove completely. Replaced by `VECTORIA_OPENAI_MODEL`, `VECTORIA_GEMINI_MODEL`, etc. |
| `vectoria/generation/llm_client.py` | 24 | Legacy fallback reading `VECTORIA_LLM_API_KEY` | ❌ Remove fallback. Use provider-specific environment variables. |
| `docs/deployment.md` | 12, 14 | Legacy documentation references | ❌ Update docs to use `VECTORIA_GEMINI_API_KEY` and provider-specific variables. |

---

## Action Plan
1. Purge `vectoria_llm_provider`, `vectoria_llm_api_key`, and `vectoria_model_name` from `backend/core/config.py`.
2. Ensure every provider owns its explicit namespace in `Settings`.
3. Create `backend/core/config_validator.py` to enforce strict startup validation without silent fallbacks.
4. Refactor `ProviderFactory` into a pure dependency injector with zero hardcoded model strings.

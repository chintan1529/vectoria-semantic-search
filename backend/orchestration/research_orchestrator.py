import json
import logging
import time
from typing import AsyncGenerator, List, Dict, Any
from sse_starlette.sse import ServerSentEvent
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    """
    Agentic Research Mode Pipeline.
    1. Multi-query expansion
    2. Parallel retrieval
    3. Contradiction detection & Synthesis
    """
    def __init__(self, provider: BaseLLMProvider, retriever: RetrievalOrchestrator):
        self.provider = provider
        self.retriever = retriever

    async def stream_research(self, query: str) -> AsyncGenerator[ServerSentEvent, None]:
        request_id = f"res_{int(time.time())}"
        
        # 1. Multi-query expansion
        yield ServerSentEvent(event="phase", data=json.dumps({"phase": "expanding"}))
        expansion_prompt = f"Expand this research query into 3 distinct, highly targeted search sub-queries to gather comprehensive evidence:\n{query}\nOutput strictly as a JSON list of 3 strings."
        messages = [{"role": "system", "content": "You are a research assistant."}, {"role": "user", "content": expansion_prompt}]
        
        try:
            exp_res = await self.provider.generate(messages, temperature=0.3)
            text = exp_res.text.strip()
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            sub_queries = json.loads(text.strip())
            if not isinstance(sub_queries, list): sub_queries = [query]
        except Exception as e:
            logger.error(f"Expansion failed: {e}")
            sub_queries = [query]
            
        yield ServerSentEvent(event="sub_queries", data=json.dumps(sub_queries))
        
        # 2. Parallel Retrieval
        yield ServerSentEvent(event="phase", data=json.dumps({"phase": "retrieving"}))
        
        all_results = []
        for sq in sub_queries:
            results, diag = self.retriever.retrieve(sq, fetch_k=10, top_k=3)
            all_results.extend(results)
            
        # Deduplicate by chunk_id
        unique_results = []
        seen_ids = set()
        for r in all_results:
            if r.chunk.chunk_id not in seen_ids:
                seen_ids.add(r.chunk.chunk_id)
                unique_results.append(r)
                
        # Limit to top 10 unique chunks
        unique_results = sorted(unique_results, key=lambda x: x.score, reverse=True)[:10]
        
        context_data = [{"id": r.chunk.chunk_id, "title": r.chunk.metadata.title, "score": r.score, "text": r.chunk.text} for r in unique_results]
        yield ServerSentEvent(event="context", data=json.dumps(context_data))
        
        # 3. Synthesis & Generation
        yield ServerSentEvent(event="phase", data=json.dumps({"phase": "generating"}))
        
        context_blocks = []
        for i, res in enumerate(unique_results, 1):
            context_blocks.append(f"[Chunk ID: {res.chunk.chunk_id} | Title: {res.chunk.metadata.title}]\n{res.chunk.text}")
        context_text = "\n\n".join(context_blocks)
        
        sys_prompt = (
            "You are a Senior Research Analyst. Your task is to write a comprehensive consensus report based on the provided evidence.\n"
            "Workflow:\n"
            "1. Synthesize the evidence.\n"
            "2. Identify any disagreements or contradictions between the sources.\n"
            "3. State your final conclusions with confidence levels.\n"
            "4. You MUST cite your sources using <cite chunk_id=\"X\"></cite> at the end of sentences.\n"
            "Format the output elegantly with Markdown headings (e.g., # Consensus Findings, # Disagreements, # Conclusion)."
        )
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Original Query: {query}\n\nEvidence Context:\n{context_text}"}
        ]
        
        token_count = 0
        async for chunk in self.provider.stream(messages):
            if hasattr(chunk, 'type'):
                if chunk.type == "token":
                    yield ServerSentEvent(event="token", data=json.dumps({"text": chunk.content}))
                    token_count += 1
                elif chunk.type == "failover":
                    yield ServerSentEvent(event=chunk.content.get("event", "provider_failover"), data=json.dumps(chunk.content))
            else:
                yield ServerSentEvent(event="token", data=json.dumps({"text": chunk}))
                token_count += 1
            
        yield ServerSentEvent(event="done", data=json.dumps({"token_count": token_count, "request_id": request_id}))

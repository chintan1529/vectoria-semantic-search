import json
import logging
from typing import List, Dict, Any

from backend.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    """
    Extracts entities and relationships from context dynamically.
    """
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider
        
    async def extract_graph(self, context_texts: List[str]) -> Dict[str, Any]:
        """
        Extracts a knowledge graph from a list of context texts.
        Returns JSON: { "nodes": [{"id": "...", "label": "...", "group": "..."}], "links": [{"source": "...", "target": "...", "label": "..."}] }
        """
        combined_text = "\n\n".join(context_texts[:5]) # Limit to top 5 for speed
        
        system_prompt = (
            "You are an expert knowledge graph extractor. "
            "Analyze the provided text and extract the key entities and the relationships between them. "
            "Output strictly valid JSON with this exact schema:\n"
            "{\n"
            "  \"nodes\": [\n"
            "    {\"id\": \"Entity Name\", \"label\": \"Entity Name\", \"group\": \"Person|Organization|Concept|Location|Technology\"}\n"
            "  ],\n"
            "  \"links\": [\n"
            "    {\"source\": \"Entity1\", \"target\": \"Entity2\", \"label\": \"Relationship Description\"}\n"
            "  ]\n"
            "}\n"
            "Keep the graph concise (max 15 nodes, max 20 links). Do not hallucinate entities."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TEXT:\n{combined_text}"}
        ]
        
        try:
            response = await self.provider.generate(messages, temperature=0.0)
            text = response.text.strip()
            
            # Clean up markdown JSON block if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            graph_data = json.loads(text.strip())
            
            # Validate format
            if "nodes" not in graph_data or "links" not in graph_data:
                raise ValueError("Invalid graph schema")
                
            return graph_data
        except Exception as e:
            logger.error(f"Failed to extract knowledge graph: {str(e)}")
            return {"nodes": [], "links": []}

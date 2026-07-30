import os
import sys
import json
import random
import time
import re
from datetime import datetime
from pathlib import Path

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.config import settings
from backend.providers.factory import ProviderFactory
from vectoria.storage import load_chunks
from colorama import Fore, Style, init

init(autoreset=True)

DATASET_DIR = Path("data/evaluation/datasets")
DATASET_DIR.mkdir(parents=True, exist_ok=True)

def get_next_version() -> str:
    files = list(DATASET_DIR.glob("dataset_v*.json"))
    if not files:
        return "v1"
    versions = []
    for f in files:
        match = re.search(r"dataset_v(\d+)\.json", f.name)
        if match:
            versions.append(int(match.group(1)))
    next_v = max(versions) + 1 if versions else 1
    return f"v{next_v}"

def generate_deterministic_questions(chunks: list, count: int) -> list:
    print(f"Generating {count} deterministic questions...")
    questions = []
    
    # Simple heuristic to find definitional or factual claims
    for chunk in chunks:
        if len(questions) >= count:
            break
            
        text = chunk.text
        # Extract potential concepts (capitalized words)
        words = text.split()
        concepts = [w.strip('.,()') for w in words if w.istitle() and len(w) > 3]
        if not concepts:
            continue
            
        concept = random.choice(concepts)
        
        category = random.choice(["Factual", "Analytical"])
        if category == "Factual":
            query = f"What is the definition or role of {concept}?"
        else:
            query = f"Explain the context surrounding {concept}."
            
        questions.append({
            "id": f"det_{len(questions)}",
            "query": query,
            "category": category,
            "difficulty": "Medium",
            "topic": chunk.metadata.category,
            "expected_concepts": [concept.lower()],
            "expected_sources": [chunk.chunk_id],
            "expected_answer_summary": text[:200] + "..."
        })
        
    # Pad if not enough
    while len(questions) < count:
        q = questions[random.randint(0, len(questions)-1)].copy()
        q["id"] = f"det_{len(questions)}"
        questions.append(q)
        
    return questions

async def generate_llm_questions(chunks: list, count: int) -> list:
    print(f"Generating {count} LLM-driven questions...")
    questions = []
    
    provider = ProviderFactory.create_research_provider()
    if not provider:
        print("Failed to initialize LLM provider. Aborting LLM generation.")
        return questions

    categories = ["Comparison", "Multi-Hop", "Analytical", "Factual"]
    
    batch_size = 5
    for i in range(0, count, batch_size):
        sampled_chunks = random.sample(chunks, 2)
        chunk1 = sampled_chunks[0]
        chunk2 = sampled_chunks[1]
        
        cat = categories[(i // batch_size) % len(categories)]
        
        prompt = f"""
        You are an expert AI Benchmark Engineer. 
        Based on the following two context chunks, generate {batch_size} high-quality '{cat}' questions.
        Return ONLY valid JSON format:
        [
          {{
            "query": "The question text",
            "expected_concepts": ["concept1", "concept2"],
            "expected_answer_summary": "Brief correct answer",
            "difficulty": "Hard"
          }}
        ]
        
        Context 1 ({chunk1.chunk_id}): {chunk1.text}
        Context 2 ({chunk2.chunk_id}): {chunk2.text}
        """
        
        messages = [{"role": "user", "content": prompt}]
        try:
            res = await provider.generate(messages, temperature=0.7)
            text = res.text
            
            # Extract JSON block
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            parsed = json.loads(text.strip())
            for idx, item in enumerate(parsed):
                if len(questions) >= count: break
                item["id"] = f"llm_{len(questions)}"
                item["category"] = cat
                item["topic"] = chunk1.metadata.category
                item["expected_sources"] = [chunk1.chunk_id, chunk2.chunk_id]
                questions.append(item)
                
            print(f"  Generated {len(questions)}/{count} LLM questions...")
            
        except Exception as e:
            print(f"  Failed to generate batch: {e}")
            
    return questions

async def main():
    print(f"{Fore.CYAN}Loading Vectoria chunks...")
    chunks = load_chunks()
    print(f"{Fore.GREEN}Loaded {len(chunks)} chunks.")
    
    det_qs = generate_deterministic_questions(chunks, 80)
    llm_qs = await generate_llm_questions(chunks, 120)
    
    dataset = det_qs + llm_qs
    
    version = get_next_version()
    
    output = {
        "metadata": {
            "version": version,
            "generation_date": datetime.now().isoformat(),
            "generator_version": "vectoria-gen-v1",
            "corpus_version": len(chunks),
            "total_questions": len(dataset)
        },
        "questions": dataset
    }
    
    output_path = DATASET_DIR / f"dataset_{version}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"{Fore.GREEN}Dataset {version} saved to {output_path} with {len(dataset)} questions.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

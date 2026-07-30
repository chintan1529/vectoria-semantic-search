import asyncio
import json
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.providers.factory import ProviderFactory

async def generate_external_questions(provider, count: int, category: str) -> list:
    print(f"Generating {count} {category} external questions...")
    prompt = f"""
    You are an expert AI evaluator creating benchmark questions.
    Generate {count} {category} questions that require deep general knowledge or logical reasoning, 
    but DO NOT reference any specific internal company data.
    
    If category is 'Adversarial', include contradictions, missing evidence scenarios, or false assumptions 
    in the premise of the questions to test the model's ability to refuse or correct the user.
    
    Output strictly as a JSON list of objects:
    [
        {{"query": "The question", "expected_answer": "Brief expected behavior/answer", "category": "{category}"}}
    ]
    Do not output markdown codeblocks, only pure JSON.
    """
    
    try:
        res = await provider.generate([{"role": "user", "content": prompt}], temperature=0.7)
        text = res.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        data = json.loads(text.strip())
        return data
    except Exception as e:
        print(f"Failed to generate {category} batch: {e}")
        return []

async def main():
    provider = ProviderFactory.create_research_provider()
    
    general = await generate_external_questions(provider, 25, "General")
    adversarial = await generate_external_questions(provider, 25, "Adversarial")
    
    dataset = {
        "metadata": {
            "version": "dataset_external_v1",
            "type": "external_generalization",
            "total": len(general) + len(adversarial)
        },
        "questions": general + adversarial
    }
    
    out_dir = Path("data/evaluation/datasets")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dataset_external_v1.json"
    
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Successfully generated {out_path} with {len(dataset['questions'])} questions.")

if __name__ == "__main__":
    asyncio.run(main())

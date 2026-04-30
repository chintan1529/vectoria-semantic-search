#!/usr/bin/env python3
"""
Wikipedia Article Fetcher -- Curated dataset for Vectoria semantic search.

Fetches ~200 Wikipedia articles across two focused domains (AI, Sustainability)
and saves them as clean .txt files compatible with the existing ingestion pipeline.

Each file is saved with a structured YAML-style header containing metadata
(title, source URL, category, fetch timestamp).

Usage:
    python scripts/fetch_wikipedia.py
"""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for config import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from vectoria.config import DATA_DIR

import wikipedia

# ------------------------------------------------------------------
# Curated article lists (~100 per domain)
# ------------------------------------------------------------------

AI_ARTICLES = [
    # Core AI & ML
    "Artificial intelligence", "Machine learning", "Deep learning",
    "Neural network (machine learning)", "Convolutional neural network",
    "Recurrent neural network", "Transformer (deep learning architecture)",
    "Generative adversarial network", "Autoencoder",
    "Reinforcement learning", "Supervised learning", "Unsupervised learning",
    "Transfer learning", "Feature learning", "Ensemble learning",
    "Gradient descent", "Backpropagation", "Activation function",
    "Loss function", "Overfitting",

    # NLP & Language
    "Natural language processing", "Word embedding",
    "Sentiment analysis", "Named-entity recognition",
    "Machine translation", "Text mining",
    "Information retrieval", "Question answering",
    "Chatbot", "Speech recognition",

    # Computer Vision
    "Computer vision", "Image classification",
    "Object detection", "Image segmentation",
    "Facial recognition system", "Optical character recognition",
    "Generative model", "Diffusion model",

    # Classical AI & Search
    "Expert system", "Knowledge representation and reasoning",
    "Bayesian network", "Decision tree",
    "Random forest", "Support-vector machine",
    "K-nearest neighbors algorithm", "Naive Bayes classifier",
    "Logistic regression", "Linear regression",
    "Principal component analysis", "Cluster analysis",
    "K-means clustering", "Dimensionality reduction",

    # Robotics & Agents
    "Robotics", "Autonomous robot",
    "Multi-agent system", "Intelligent agent",
    "Swarm intelligence", "Evolutionary algorithm",
    "Genetic algorithm", "Particle swarm optimization",

    # Modern AI Systems
    "Recommender system", "Artificial neural network",
    "Long short-term memory", "Attention (machine learning)",
    "Batch normalization", "Dropout (neural networks)",
    "Data augmentation", "Hyperparameter optimization",
    "Neural architecture search", "AutoML",
    "Federated learning", "Edge computing",
    "Explainable artificial intelligence", "AI safety",
    "Existential risk from artificial general intelligence",
    "Artificial general intelligence",

    # Data & Infrastructure
    "Big data", "Data mining", "Data science",
    "Feature engineering", "Cross-validation (statistics)",
    "Bias-variance tradeoff", "Regularization (mathematics)",
    "Stochastic gradient descent", "Adam (optimization algorithm)",

    # Applications
    "AlphaGo", "GPT-4",
    "Self-driving car", "Medical image computing",
    "Drug discovery", "Protein structure prediction",
    "Game artificial intelligence",
    "Turing test",
]

SUSTAINABILITY_ARTICLES = [
    # Climate Science
    "Climate change", "Global warming", "Greenhouse gas",
    "Carbon dioxide in Earth's atmosphere",
    "Greenhouse effect", "Climate change feedback",
    "Sea level rise", "Ocean acidification",
    "Global warming potential", "Carbon cycle",
    "Paleoclimatology", "Climate model",
    "Effects of climate change", "Attribution of recent climate change",

    # Energy
    "Renewable energy", "Solar energy", "Wind power",
    "Hydroelectricity", "Geothermal energy",
    "Nuclear power", "Fossil fuel",
    "Energy storage", "Battery storage power station",
    "Smart grid", "Energy efficiency",
    "Solar panel", "Wind turbine",
    "Photovoltaic system", "Concentrated solar power",
    "Offshore wind power", "Tidal power",
    "Hydrogen economy", "Green hydrogen",

    # Environment
    "Deforestation", "Biodiversity loss",
    "Ecosystem", "Ecological footprint",
    "Water scarcity", "Desertification",
    "Coral reef", "Amazon rainforest",
    "Wetland", "Permafrost",
    "Air pollution", "Water pollution",
    "Plastic pollution", "Electronic waste",
    "Ozone depletion", "Acid rain",

    # Sustainability Concepts
    "Sustainable development", "Circular economy",
    "Carbon footprint", "Carbon neutrality",
    "Net zero emissions", "Carbon capture and storage",
    "Emissions trading", "Carbon tax",
    "Paris Agreement", "Kyoto Protocol",
    "Intergovernmental Panel on Climate Change",
    "United Nations Environment Programme",
    "Sustainable Development Goals",

    # Agriculture & Food
    "Sustainable agriculture", "Organic farming",
    "Precision agriculture", "Vertical farming",
    "Food security", "Agroecology",
    "Irrigation", "Soil degradation",

    # Transportation
    "Electric vehicle", "Public transport",
    "High-speed rail", "Bicycle-sharing system",
    "Sustainable transport", "Aviation and the environment",

    # Urban & Social
    "Green building", "Urban planning",
    "Smart city", "Waste management",
    "Recycling", "Zero waste",
    "Environmental justice", "Climate justice",
    "Environmental policy", "Greenwashing",

    # Conservation
    "Conservation biology", "Wildlife conservation",
    "Marine protected area", "National park",
    "Endangered species", "Habitat destruction",
    "Invasive species", "Reforestation",
]


# ------------------------------------------------------------------
# Fetcher logic
# ------------------------------------------------------------------


def sanitize_filename(title: str) -> str:
    """Convert article title to a safe filename."""
    name = title.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name[:80]  # cap length


def build_header(title: str, url: str, category: str) -> str:
    """Build a YAML-style metadata header for the text file."""
    ts = datetime.now(timezone.utc).isoformat()
    return (
        f"---\n"
        f"title: {title}\n"
        f"source: {url}\n"
        f"category: {category}\n"
        f"timestamp: {ts}\n"
        f"---\n\n"
    )


def fetch_article(title: str, category: str, output_dir: Path) -> dict:
    """Fetch a single Wikipedia article and save it.

    Returns a dict with status info.
    """
    fname = sanitize_filename(title) + ".txt"
    fpath = output_dir / fname

    # Skip if already exists
    if fpath.exists():
        return {"title": title, "status": "skipped_exists", "words": 0}

    # Retry logic for transient API failures
    max_retries = 3
    page = None

    for attempt in range(max_retries):
        try:
            page = wikipedia.page(title, auto_suggest=False)
            break
        except wikipedia.DisambiguationError:
            return {"title": title, "status": "disambiguation", "words": 0}
        except wikipedia.PageError:
            return {"title": title, "status": "not_found", "words": 0}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # exponential backoff
                continue
            return {"title": title, "status": f"error:{type(e).__name__}", "words": 0}

    if page is None:
        return {"title": title, "status": "error:no_page", "words": 0}

    # Get content with retry
    content = None
    for attempt in range(max_retries):
        try:
            content = page.content
            break
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue

    if content is None:
        return {"title": title, "status": "error:content_fetch", "words": 0}

    # Clean content
    # Remove Wikipedia section markers like == Heading ==
    content = re.sub(r"={2,}\s*[^=]+\s*={2,}", "", content)
    # Remove excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = content.strip()

    word_count = len(content.split())

    # Skip very short articles
    if word_count < 500:
        return {"title": title, "status": "too_short", "words": word_count}

    # Build file with header + content
    try:
        url = page.url
    except Exception:
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

    header = build_header(title, url, category)
    full_text = header + content

    fpath.write_text(full_text, encoding="utf-8")

    return {"title": title, "status": "saved", "words": word_count, "path": str(fpath)}


def fetch_domain(
    articles: list[str],
    category: str,
    output_dir: Path,
    delay: float = 0.5,
) -> list[dict]:
    """Fetch all articles for a domain with rate limiting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    total = len(articles)
    for i, title in enumerate(articles, 1):
        print(f"  [{category}] {i:3d}/{total} Fetching: {title[:50]}...", end="")
        result = fetch_article(title, category, output_dir)
        results.append(result)

        status = result["status"]
        if status == "saved":
            print(f" OK ({result['words']}w)")
        elif status == "skipped_exists":
            print(f" SKIP (exists)")
        else:
            print(f" {status.upper()}")

        # Rate limiting (skip delay for cached/skipped)
        if status not in ("skipped_exists",):
            time.sleep(delay)

    return results


def print_summary(results: list[dict], category: str) -> None:
    """Print fetch summary for a domain."""
    saved = [r for r in results if r["status"] == "saved"]
    skipped = [r for r in results if r["status"] == "skipped_exists"]
    failed = [r for r in results if r["status"] not in ("saved", "skipped_exists")]
    total_words = sum(r.get("words", 0) for r in saved + skipped)
    avg_words = total_words // max(len(saved) + len(skipped), 1)

    print(f"\n  [{category.upper()}] SUMMARY")
    print(f"  {'-' * 40}")
    print(f"  Requested:  {len(results)}")
    print(f"  Saved:      {len(saved)}")
    print(f"  Existed:    {len(skipped)}")
    print(f"  Failed:     {len(failed)}")
    if failed:
        for r in failed[:5]:
            print(f"    - {r['title']}: {r['status']}")
    print(f"  Total words: {total_words:,}")
    print(f"  Avg words:   {avg_words}")


def validate_dataset(data_dir: Path) -> None:
    """Validate the fetched dataset."""
    print("\n" + "=" * 60)
    print("  DATASET VALIDATION")
    print("=" * 60)

    ai_dir = data_dir / "ai"
    sus_dir = data_dir / "sustainability"

    ai_files = list(ai_dir.glob("*.txt")) if ai_dir.exists() else []
    sus_files = list(sus_dir.glob("*.txt")) if sus_dir.exists() else []
    all_files = ai_files + sus_files

    total_words = 0
    word_counts = []
    for f in all_files:
        text = f.read_text(encoding="utf-8")
        # Skip header lines for word count
        lines = text.split("\n")
        body_start = 0
        for i, line in enumerate(lines):
            if line.strip() == "---" and i > 0:
                body_start = i + 1
                break
        body = "\n".join(lines[body_start:])
        wc = len(body.split())
        word_counts.append(wc)
        total_words += wc

    avg_words = total_words // max(len(all_files), 1)

    print(f"\n  Directory: {data_dir}")
    print(f"  AI articles:             {len(ai_files)}")
    print(f"  Sustainability articles: {len(sus_files)}")
    print(f"  Total articles:          {len(all_files)}")
    print(f"  Total words:             {total_words:,}")
    print(f"  Average words/article:   {avg_words}")
    if word_counts:
        print(f"  Min words:               {min(word_counts)}")
        print(f"  Max words:               {max(word_counts)}")

    # Checks
    checks = {
        "file_count >= 150": len(all_files) >= 150,
        "avg_words >= 500": avg_words >= 500,
        "ai_dir exists": ai_dir.exists(),
        "sustainability_dir exists": sus_dir.exists(),
    }
    print(f"\n  CHECKS:")
    all_ok = True
    for check, ok in checks.items():
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"    [{status}] {check}")

    if all_ok:
        print("\n  [OK] DATASET READY")
    else:
        print("\n  [WARN] Some checks failed — re-run to fetch more articles")


def main() -> None:
    print("=" * 60)
    print("  WIKIPEDIA DATASET FETCHER")
    print("=" * 60)
    print()

    start = time.perf_counter()

    # -- Fetch AI articles ---------------------------------------------
    print("  Fetching AI / Machine Learning articles...")
    ai_results = fetch_domain(
        AI_ARTICLES, "ai", DATA_DIR / "ai", delay=0.5
    )
    print_summary(ai_results, "ai")

    # -- Fetch Sustainability articles ---------------------------------
    print(f"\n  Fetching Sustainability / Environment articles...")
    sus_results = fetch_domain(
        SUSTAINABILITY_ARTICLES, "sustainability",
        DATA_DIR / "sustainability", delay=0.5
    )
    print_summary(sus_results, "sustainability")

    elapsed = time.perf_counter() - start
    print(f"\n  Total fetch time: {elapsed:.0f}s ({elapsed/60:.1f}m)")

    # -- Validate ------------------------------------------------------
    validate_dataset(DATA_DIR)


if __name__ == "__main__":
    main()

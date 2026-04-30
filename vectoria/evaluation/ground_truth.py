"""
Ground Truth -- Domain-aware relevance judgments for retrieval evaluation.

This module defines evaluation queries with expected relevant domains and
keyword-based relevance grading.  Each query specifies:

- **domain**: The expected primary domain ("ai" or "sustainability").
- **keywords**: Terms that indicate relevance in retrieved chunks.
- **highly_relevant_titles**: Specific Wikipedia article titles that are
  definitively relevant (strong positive signal).

Relevance grading:
    - **Highly relevant**: chunk is from a ``highly_relevant_titles`` article.
    - **Relevant**: chunk's domain matches AND contains >=2 keywords.
    - **Weakly relevant**: chunk's domain matches the expected domain.
    - **Irrelevant**: wrong domain AND no keyword match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalQuery:
    """A single evaluation query with relevance ground truth."""

    query: str
    domain: str  # "ai" or "sustainability"
    keywords: List[str] = field(default_factory=list)
    highly_relevant_titles: List[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Curated evaluation queries (20 per domain = 40 total)
# ------------------------------------------------------------------

AI_QUERIES: List[EvalQuery] = [
    EvalQuery(
        query="How do neural networks learn from data?",
        domain="ai",
        keywords=["neural", "network", "backpropagation", "training", "gradient", "learn"],
        highly_relevant_titles=["Artificial neural network", "Backpropagation", "Deep learning"],
    ),
    EvalQuery(
        query="What is the transformer architecture used in modern NLP?",
        domain="ai",
        keywords=["transformer", "attention", "self-attention", "NLP", "language model"],
        highly_relevant_titles=["Transformer (deep learning architecture)", "Attention (machine learning)"],
    ),
    EvalQuery(
        query="How does reinforcement learning work?",
        domain="ai",
        keywords=["reinforcement", "reward", "policy", "agent", "environment", "Q-learning"],
        highly_relevant_titles=["Reinforcement learning"],
    ),
    EvalQuery(
        query="What are convolutional neural networks used for?",
        domain="ai",
        keywords=["convolutional", "CNN", "image", "filter", "pooling", "feature map"],
        highly_relevant_titles=["Convolutional neural network", "Computer vision"],
    ),
    EvalQuery(
        query="Explain the concept of overfitting in machine learning",
        domain="ai",
        keywords=["overfitting", "generalization", "regularization", "training", "validation"],
        highly_relevant_titles=["Overfitting", "Regularization (mathematics)"],
    ),
    EvalQuery(
        query="What is transfer learning and why is it useful?",
        domain="ai",
        keywords=["transfer", "pretrained", "fine-tuning", "domain adaptation"],
        highly_relevant_titles=["Transfer learning", "Feature learning"],
    ),
    EvalQuery(
        query="How do generative adversarial networks create images?",
        domain="ai",
        keywords=["GAN", "generator", "discriminator", "adversarial", "generative"],
        highly_relevant_titles=["Generative adversarial network", "Generative model"],
    ),
    EvalQuery(
        query="What is the difference between supervised and unsupervised learning?",
        domain="ai",
        keywords=["supervised", "unsupervised", "labeled", "clustering", "classification"],
        highly_relevant_titles=["Supervised learning", "Unsupervised learning", "Machine learning"],
    ),
    EvalQuery(
        query="How does natural language processing handle text understanding?",
        domain="ai",
        keywords=["NLP", "language", "text", "parsing", "semantics", "tokenization"],
        highly_relevant_titles=["Natural language processing", "Text mining"],
    ),
    EvalQuery(
        query="What is sentiment analysis and how is it applied?",
        domain="ai",
        keywords=["sentiment", "opinion", "polarity", "classification", "text"],
        highly_relevant_titles=["Sentiment analysis", "Natural language processing"],
    ),
    EvalQuery(
        query="How do decision trees make predictions?",
        domain="ai",
        keywords=["decision tree", "split", "leaf", "entropy", "information gain"],
        highly_relevant_titles=["Decision tree", "Random forest"],
    ),
    EvalQuery(
        query="What is the support vector machine algorithm?",
        domain="ai",
        keywords=["SVM", "support vector", "hyperplane", "kernel", "margin"],
        highly_relevant_titles=["Support-vector machine"],
    ),
    EvalQuery(
        query="How does gradient descent optimize neural networks?",
        domain="ai",
        keywords=["gradient", "descent", "learning rate", "loss", "optimization", "convergence"],
        highly_relevant_titles=["Gradient descent", "Stochastic gradient descent", "Backpropagation"],
    ),
    EvalQuery(
        query="What are recurrent neural networks and LSTM?",
        domain="ai",
        keywords=["recurrent", "RNN", "LSTM", "sequence", "memory", "hidden state"],
        highly_relevant_titles=["Recurrent neural network", "Long short-term memory"],
    ),
    EvalQuery(
        query="How do recommender systems suggest products?",
        domain="ai",
        keywords=["recommender", "collaborative", "filtering", "preference", "rating"],
        highly_relevant_titles=["Recommender system"],
    ),
    EvalQuery(
        query="What is computer vision and object detection?",
        domain="ai",
        keywords=["computer vision", "object detection", "image", "recognition", "bounding box"],
        highly_relevant_titles=["Computer vision", "Object detection", "Image classification"],
    ),
    EvalQuery(
        query="How does AlphaGo use artificial intelligence to play Go?",
        domain="ai",
        keywords=["AlphaGo", "Go", "Monte Carlo", "tree search", "reinforcement"],
        highly_relevant_titles=["AlphaGo", "Reinforcement learning"],
    ),
    EvalQuery(
        query="What is explainable AI and why does it matter?",
        domain="ai",
        keywords=["explainable", "interpretable", "transparency", "black box", "XAI"],
        highly_relevant_titles=["Explainable artificial intelligence", "AI safety"],
    ),
    EvalQuery(
        query="How is AI used in drug discovery and protein prediction?",
        domain="ai",
        keywords=["drug", "protein", "molecular", "prediction", "AlphaFold", "discovery"],
        highly_relevant_titles=["Drug discovery", "Protein structure prediction"],
    ),
    EvalQuery(
        query="What are the risks of artificial general intelligence?",
        domain="ai",
        keywords=["AGI", "existential", "risk", "superintelligence", "alignment", "safety"],
        highly_relevant_titles=[
            "Artificial general intelligence",
            "Existential risk from artificial general intelligence",
            "AI safety",
        ],
    ),
]

SUSTAINABILITY_QUERIES: List[EvalQuery] = [
    EvalQuery(
        query="What causes climate change and global warming?",
        domain="sustainability",
        keywords=["climate", "warming", "greenhouse", "CO2", "temperature", "emission"],
        highly_relevant_titles=["Climate change", "Global warming", "Greenhouse gas"],
    ),
    EvalQuery(
        query="How does sea level rise affect coastal communities?",
        domain="sustainability",
        keywords=["sea level", "coastal", "flooding", "ice", "thermal expansion"],
        highly_relevant_titles=["Sea level rise", "Effects of climate change"],
    ),
    EvalQuery(
        query="What are the benefits of renewable energy sources?",
        domain="sustainability",
        keywords=["renewable", "solar", "wind", "clean", "sustainable", "energy"],
        highly_relevant_titles=["Renewable energy", "Solar energy", "Wind power"],
    ),
    EvalQuery(
        query="How does deforestation contribute to biodiversity loss?",
        domain="sustainability",
        keywords=["deforestation", "biodiversity", "habitat", "species", "forest", "ecosystem"],
        highly_relevant_titles=["Deforestation", "Biodiversity loss", "Habitat destruction"],
    ),
    EvalQuery(
        query="What is the Paris Agreement on climate change?",
        domain="sustainability",
        keywords=["Paris", "agreement", "treaty", "emission", "target", "UNFCCC"],
        highly_relevant_titles=["Paris Agreement", "Kyoto Protocol"],
    ),
    EvalQuery(
        query="How do solar panels convert sunlight to electricity?",
        domain="sustainability",
        keywords=["solar", "photovoltaic", "cell", "panel", "sunlight", "electricity"],
        highly_relevant_titles=["Solar panel", "Photovoltaic system", "Solar energy"],
    ),
    EvalQuery(
        query="What is carbon capture and storage technology?",
        domain="sustainability",
        keywords=["carbon capture", "CCS", "storage", "sequestration", "CO2"],
        highly_relevant_titles=["Carbon capture and storage", "Carbon neutrality"],
    ),
    EvalQuery(
        query="How does plastic pollution affect marine ecosystems?",
        domain="sustainability",
        keywords=["plastic", "pollution", "marine", "ocean", "microplastic", "waste"],
        highly_relevant_titles=["Plastic pollution", "Ocean acidification"],
    ),
    EvalQuery(
        query="What are the goals of sustainable development?",
        domain="sustainability",
        keywords=["sustainable development", "SDG", "goals", "poverty", "equity"],
        highly_relevant_titles=["Sustainable Development Goals", "Sustainable development"],
    ),
    EvalQuery(
        query="How does the circular economy reduce waste?",
        domain="sustainability",
        keywords=["circular", "economy", "waste", "reuse", "recycle", "lifecycle"],
        highly_relevant_titles=["Circular economy", "Recycling", "Zero waste"],
    ),
    EvalQuery(
        query="What is the role of electric vehicles in reducing emissions?",
        domain="sustainability",
        keywords=["electric", "vehicle", "EV", "emission", "battery", "transport"],
        highly_relevant_titles=["Electric vehicle", "Sustainable transport"],
    ),
    EvalQuery(
        query="How does ocean acidification affect coral reefs?",
        domain="sustainability",
        keywords=["ocean", "acidification", "coral", "reef", "pH", "carbonate"],
        highly_relevant_titles=["Ocean acidification", "Coral reef"],
    ),
    EvalQuery(
        query="What is the carbon footprint and how is it measured?",
        domain="sustainability",
        keywords=["carbon footprint", "emission", "measure", "CO2", "lifecycle"],
        highly_relevant_titles=["Carbon footprint", "Ecological footprint", "Carbon neutrality"],
    ),
    EvalQuery(
        query="How does wind power generate electricity?",
        domain="sustainability",
        keywords=["wind", "turbine", "rotor", "blade", "electricity", "offshore"],
        highly_relevant_titles=["Wind power", "Wind turbine", "Offshore wind power"],
    ),
    EvalQuery(
        query="What is the greenhouse effect and how does it work?",
        domain="sustainability",
        keywords=["greenhouse", "effect", "radiation", "atmosphere", "infrared", "trap"],
        highly_relevant_titles=["Greenhouse effect", "Greenhouse gas"],
    ),
    EvalQuery(
        query="How does permafrost thawing affect climate change?",
        domain="sustainability",
        keywords=["permafrost", "thaw", "methane", "carbon", "arctic", "feedback"],
        highly_relevant_titles=["Permafrost", "Climate change feedback"],
    ),
    EvalQuery(
        query="What is sustainable agriculture and organic farming?",
        domain="sustainability",
        keywords=["sustainable", "agriculture", "organic", "farming", "soil", "pesticide"],
        highly_relevant_titles=["Sustainable agriculture", "Organic farming", "Agroecology"],
    ),
    EvalQuery(
        query="How does emissions trading work to reduce pollution?",
        domain="sustainability",
        keywords=["emissions", "trading", "cap", "trade", "allowance", "market"],
        highly_relevant_titles=["Emissions trading", "Carbon neutrality"],
    ),
    EvalQuery(
        query="What is the impact of electronic waste on the environment?",
        domain="sustainability",
        keywords=["electronic", "e-waste", "recycling", "toxic", "disposal"],
        highly_relevant_titles=["Electronic waste", "Waste management", "Recycling"],
    ),
    EvalQuery(
        query="How does reforestation help combat climate change?",
        domain="sustainability",
        keywords=["reforestation", "tree", "carbon", "sequestration", "forest", "planting"],
        highly_relevant_titles=["Reforestation", "Deforestation", "Carbon cycle"],
    ),
]

ALL_QUERIES: List[EvalQuery] = AI_QUERIES + SUSTAINABILITY_QUERIES

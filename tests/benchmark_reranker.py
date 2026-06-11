import time
from vectoria.reranking.reranker import CrossEncoderReranker
from vectoria.models import SearchResult, Chunk, DocumentMeta

def benchmark_reranker():
    print("Initializing CrossEncoderReranker...")
    reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    query = "What is backpropagation in neural networks and how does it work?"
    
    print("Warming up...")
    dummy_results = [
        SearchResult(chunk=Chunk(chunk_id=str(i), doc_id="dummy", chunk_index=i, text="Neural networks learn by adjusting weights.", metadata=DocumentMeta(doc_id="dummy", title="Doc", source="source", category="ai", timestamp="2026")), score=1.0, rank=i)
        for i in range(2)
    ]
    reranker.rerank(query, dummy_results)
    
    candidate_counts = [30, 20, 15, 10]
    
    for count in candidate_counts:
        results = [
            SearchResult(chunk=Chunk(chunk_id=str(i), doc_id="dummy", chunk_index=i, text="Backpropagation is an algorithm used in artificial neural networks to calculate the gradient of the error function with respect to the neural network's weights. It is a generalization of the delta rule for perceptrons to multilayer feedforward neural networks." * 2, metadata=DocumentMeta(doc_id="dummy", title="Doc", source="source", category="ai", timestamp="2026")), score=1.0, rank=i)
            for i in range(count)
        ]
        
        start = time.perf_counter()
        reranker.rerank(query, results)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"Top {count} candidates: {elapsed:.2f} ms")

benchmark_reranker()

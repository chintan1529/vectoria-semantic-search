from typing import List
from vectoria.models import SearchResult
from vectoria.performance.hardware_detector import hardware_monitor


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                torch.set_num_threads(2)
            except Exception:
                pass
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
        return self._model

    def preload(self) -> None:
        """Eagerly preloads CrossEncoder model weights and runs a full candidate batch forward pass during startup."""
        model = self._get_model()
        try:
            import torch
            with torch.no_grad():
                model.predict([("warmup query", "warmup text chunk")] * 15, batch_size=self.batch_size, show_progress_bar=False)
        except Exception:
            pass

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        if not results:
            return []

        model = self._get_model()
        pairs = [(query, r.chunk.text) for r in results]

        try:
            import torch
            with torch.no_grad():
                scores = model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        except ImportError:
            scores = model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)

        for i, result in enumerate(results):
            result.score = float(scores[i])

        results.sort(key=lambda r: (-r.score, r.chunk.chunk_id))
        return results

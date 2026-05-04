from typing import List

from vectoria.models import SearchResult


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
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        if not results:
            return []

        model = self._get_model()

        pairs = [(query, r.chunk.text) for r in results]

        scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            truncation=True
        )

        for i, result in enumerate(results):
            result.score = float(scores[i])

        results.sort(key=lambda r: (-r.score, r.chunk.chunk_id))

        return results

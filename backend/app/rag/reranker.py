import logging
import threading
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = settings.RERANKER_MODEL or model_name
        self._model = None
        self._failed = False
        self._loading = False
        self._lock = threading.Lock()

    def _load_model_sync(self):
        with self._lock:
            if self._model is not None or self._failed:
                return
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading cross-encoder reranker model in background: {self.model_name}")
                self._model = CrossEncoder(self.model_name)
                logger.info(f"Cross-encoder reranker '{self.model_name}' successfully loaded.")
            except Exception as e:
                logger.warning(f"Could not load reranker model '{self.model_name}': {e}. Using retrieval score ranking.")
                self._failed = True
            finally:
                self._loading = False

    def trigger_background_load(self):
        if self._model is None and not self._loading and not self._failed:
            self._loading = True
            thread = threading.Thread(target=self._load_model_sync, daemon=True)
            thread.start()

    @property
    def model(self):
        self.trigger_background_load()
        return self._model

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks retrieved candidate chunks.
        Caps candidate pool to top 8 to minimize cross-encoder latency.
        """
        if not documents:
            return []
            
        if len(documents) <= 1:
            return documents[:top_k]

        # Ensure background loading is initiated
        self.trigger_background_load()

        # Limit candidates passed into cross-encoder for sub-second latency
        cand_docs = documents[:4]
        model = self._model

        if model is None:
            # Zero-latency fallback: rank by precomputed RRF and vector similarity score
            sorted_docs = sorted(cand_docs, key=lambda d: float(d.get("rrf_score") or d.get("score") or 0.0), reverse=True)
            for d in sorted_docs:
                d["rerank_score"] = float(d.get("rrf_score") or d.get("score") or 0.0)
            return sorted_docs[:top_k]

        try:
            pairs = [[query, doc.get("content") or doc.get("text", "")] for doc in cand_docs]
            scores = model.predict(pairs, batch_size=4, show_progress_bar=False)
            
            scored_docs = []
            for i, doc in enumerate(cand_docs):
                doc_copy = dict(doc)
                doc_copy["rerank_score"] = float(scores[i])
                scored_docs.append(doc_copy)
                
            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
            return scored_docs[:top_k]
        except Exception as e:
            logger.error(f"Error during reranking: {e}. Returning original documents.")
            sorted_docs = sorted(cand_docs, key=lambda d: float(d.get("rrf_score") or d.get("score") or 0.0), reverse=True)
            return sorted_docs[:top_k]

reranker = Reranker()

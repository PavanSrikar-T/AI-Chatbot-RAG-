import logging
import re
import sqlite3
import os
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from rank_bm25 import BM25Okapi
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from app.rag.embedder import embedder
from app.core.vector_db import qdrant, COLLECTION_NAME

logger = logging.getLogger(__name__)

STOP_WORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 
    'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 
    'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 
    'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 
    'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 
    'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 
    'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 
    'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 
    'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'tell'
}

def is_broad_query(query: str) -> bool:
    """Detects whether a query is broad/list-seeking (projects, skills, experience, summary, etc.)"""
    q = query.lower().strip()
    if q.startswith(('which project', 'which technology', 'which company', 'what project used', 'what project is')):
        return False
    broad_patterns = [
        r'\bprojects?\b', r'\bexperiences?\b', r'\bskills?\b', r'\bcertifications?\b',
        r'\blanguages?\b', r'\beducations?\b', r'\bworked\b', r'\ball\b', r'\blist\b',
        r'\bsummar(y|ize)\b', r'\boverview\b', r'\bwhat (have i|did i|do i|are my|are the)\b',
        r'\btell me about\b'
    ]
    return any(re.search(p, q) for p in broad_patterns)

def tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    """Alphanumeric tokenizer with optional stopword filtering for BM25 precision."""
    tokens = [word.lower() for word in re.findall(r'\b\w+\b', text or "")]
    if remove_stopwords:
        filtered = [w for w in tokens if w not in STOP_WORDS and len(w) > 1]
        return filtered if filtered else tokens
    return tokens


class HybridRetriever:
    def __init__(self, collection_name: str = COLLECTION_NAME, rrf_k: int = 60):
        self.collection_name = collection_name
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "careermind.db"))
        self._bm25_cache: Dict[int, Tuple[float, BM25Okapi, List[Dict[str, Any]]]] = {}
        self._chunk_cache: Dict[int, Tuple[float, Dict[Tuple[int, int], Dict[str, Any]], Dict[str, Tuple[int, int]]]] = {}
        self._pool = ThreadPoolExecutor(max_workers=4)

    def invalidate_user_cache(self, user_id: int):
        """Clears in-memory BM25 and chunk lookup cache when user uploads new documents."""
        self._bm25_cache.pop(user_id, None)
        self._chunk_cache.pop(user_id, None)

    def dense_search(self, query: str, user_id: int, top_k: int = 15) -> List[Dict[str, Any]]:
        """Retrieve candidates using Qdrant vector similarity with mandatory user isolation."""
        try:
            query_vector = self.embedder.embed_query(query)
            
            user_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
            
            search_result = qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=user_filter,
                limit=top_k,
                with_payload=True,
            )
            
            results = []
            for hit in search_result:
                payload = hit.payload or {}
                results.append({
                    "id": str(hit.id),
                    "chunk_id": payload.get("chunk_id", str(hit.id)),
                    "document_id": payload.get("document_id"),
                    "filename": payload.get("filename", "Document"),
                    "page": payload.get("page") or payload.get("page_number", 1),
                    "page_number": payload.get("page_number") or payload.get("page", 1),
                    "content": payload.get("content") or payload.get("text", ""),
                    "section": payload.get("section", ""),
                    "score": hit.score,
                    "payload": payload,
                })
            return results
        except Exception as e:
            logger.error(f"Dense search error: {e}")
            return []

    def _get_or_build_bm25(self, user_id: int) -> Optional[Tuple[BM25Okapi, List[Dict[str, Any]]]]:
        now = time.time()
        if user_id in self._bm25_cache:
            ts, bm25_obj, docs_list = self._bm25_cache[user_id]
            if now - ts < 300.0:  # 5 min TTL
                return bm25_obj, docs_list

        user_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
        
        scroll_result, _ = qdrant.scroll(
            collection_name=self.collection_name,
            scroll_filter=user_filter,
            limit=200,
            with_payload=True,
            with_vectors=False,
        )
        
        if not scroll_result:
            return None
            
        docs = []
        corpus = []
        for point in scroll_result:
            payload = point.payload or {}
            content = payload.get("content") or payload.get("text", "")
            if not content:
                continue
            tokens = tokenize(content, remove_stopwords=False)
            if not tokens:
                continue
            corpus.append(tokens)
            docs.append({
                "id": str(point.id),
                "chunk_id": payload.get("chunk_id", str(point.id)),
                "document_id": payload.get("document_id"),
                "filename": payload.get("filename", "Document"),
                "page": payload.get("page") or payload.get("page_number", 1),
                "page_number": payload.get("page_number") or payload.get("page", 1),
                "content": content,
                "section": payload.get("section", ""),
                "payload": payload,
            })
            
        if not corpus:
            return None
            
        bm25 = BM25Okapi(corpus)
        self._bm25_cache[user_id] = (now, bm25, docs)
        return bm25, docs

    def sparse_search(self, query: str, user_id: int, top_k: int = 15) -> List[Dict[str, Any]]:
        """Retrieve candidates using fast in-memory BM25 keyword search over user's chunks."""
        try:
            cache_res = self._get_or_build_bm25(user_id)
            if not cache_res:
                return []
            bm25, docs = cache_res
                
            query_tokens = tokenize(query, remove_stopwords=True)
            if not query_tokens:
                query_tokens = tokenize(query, remove_stopwords=False)
            if not query_tokens:
                return []
                
            doc_scores = bm25.get_scores(query_tokens)
            
            scored_docs = []
            for i, score in enumerate(doc_scores):
                if score > 0:
                    scored_docs.append((score, docs[i]))
                    
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            results = []
            for score, doc in scored_docs[:top_k]:
                doc_copy = dict(doc)
                doc_copy["score"] = float(score)
                results.append(doc_copy)
                
            return results
        except Exception as e:
            logger.warning(f"Sparse search error (continuing with dense): {e}")
            return []

    def reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        top_k: int = 16
    ) -> List[Dict[str, Any]]:
        """Combine dense and sparse search rankings using Reciprocal Rank Fusion."""
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        for rank, doc in enumerate(dense_results):
            doc_id = doc.get("chunk_id") or doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.rrf_k + rank + 1))

        for rank, doc in enumerate(sparse_results):
            doc_id = doc.get("chunk_id") or doc["id"]
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.rrf_k + rank + 1))

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        final_results = []
        for doc_id in sorted_ids[:top_k]:
            item = dict(doc_map[doc_id])
            item["rrf_score"] = rrf_scores[doc_id]
            final_results.append(item)

        return final_results

    def _get_user_chunk_map(self, user_id: int):
        now = time.time()
        if user_id in self._chunk_cache:
            ts, chunk_map, id_to_meta = self._chunk_cache[user_id]
            if now - ts < 300.0:
                return chunk_map, id_to_meta

        if not os.path.exists(self.db_path):
            return {}, {}

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.page_number, dc.section, dc.content, d.filename 
            FROM document_chunks dc 
            JOIN documents d ON dc.document_id = d.id 
            WHERE d.user_id = ?
            ORDER BY dc.document_id, dc.chunk_index
        """, (user_id,))
        rows = cur.fetchall()
        conn.close()

        chunk_map = {}
        id_to_meta = {}
        for r in rows:
            c = {
                "id": r[0],
                "chunk_id": r[0],
                "document_id": r[1],
                "chunk_index": r[2],
                "page_number": r[3],
                "page": r[3],
                "section": r[4],
                "content": r[5],
                "filename": r[6]
            }
            chunk_map[(r[1], r[2])] = c
            id_to_meta[r[0]] = (r[1], r[2])

        self._chunk_cache[user_id] = (now, chunk_map, id_to_meta)
        return chunk_map, id_to_meta

    def expand_adjacent_chunks(
        self,
        candidates: List[Dict[str, Any]],
        user_id: int,
        query: str,
        is_broad: bool = True
    ) -> List[Dict[str, Any]]:
        """Intelligently expands neighboring chunks for contiguous sections while preserving user isolation."""
        if not candidates:
            return candidates

        try:
            chunk_map, id_to_meta = self._get_user_chunk_map(user_id)
            if not chunk_map:
                return candidates

            expanded_dict = {c["chunk_id"]: dict(c) for c in candidates}
            
            for cid, c in expanded_dict.items():
                if "chunk_index" not in c and cid in id_to_meta:
                    c["chunk_index"] = id_to_meta[cid][1]

            top_candidates = candidates[: (4 if is_broad else 2)]
            for c in top_candidates:
                cid = c.get("chunk_id")
                if cid not in id_to_meta:
                    continue
                doc_id, idx = id_to_meta[cid]
                base_score = c.get("rrf_score") or c.get("score") or 0.0

                hops = [1] if not is_broad else [1, 2]
                for hop in hops:
                    next_key = (doc_id, idx + hop)
                    if next_key in chunk_map:
                        neighbor = chunk_map[next_key]
                        n_lower = neighbor["content"].lower()
                        if "i hereby declare that all the information" in n_lower or "declaration" in n_lower:
                            continue
                        
                        if neighbor["chunk_id"] not in expanded_dict:
                            n_copy = dict(neighbor)
                            n_copy["rrf_score"] = base_score * 0.95
                            n_copy["score"] = base_score * 0.95
                            expanded_dict[neighbor["chunk_id"]] = n_copy

            return list(expanded_dict.values())
        except Exception as e:
            logger.warning(f"Adjacent chunk expansion error: {e}")
            return candidates

    def retrieve(
        self,
        query: str,
        user_id: int,
        top_k: int = 15,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute parallel hybrid retrieval with candidate budgeting and strict user isolation.
        """
        is_broad = is_broad_query(query)
        cand_top_k = max(top_k, 14 if is_broad else 8)

        if not use_hybrid:
            candidates = self.dense_search(query, user_id=user_id, top_k=cand_top_k)
        else:
            # Parallel execution of dense search and sparse search
            fut_dense = self._pool.submit(self.dense_search, query, user_id, cand_top_k)
            fut_sparse = self._pool.submit(self.sparse_search, query, user_id, cand_top_k)
            
            dense_results = fut_dense.result()
            sparse_results = fut_sparse.result()

            if not sparse_results:
                candidates = dense_results
            else:
                candidates = self.reciprocal_rank_fusion(dense_results, sparse_results, top_k=cand_top_k)

        # Expand adjacent chunks for contiguous section coverage
        expanded_candidates = self.expand_adjacent_chunks(candidates, user_id=user_id, query=query, is_broad=is_broad)
        return expanded_candidates


retriever = HybridRetriever()


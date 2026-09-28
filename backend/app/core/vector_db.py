import logging
import time
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchValue, FilterSelector, PayloadSchemaType
from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "careermind_documents"
import threading
_qdrant_instance: Optional[QdrantClient] = None
_qdrant_lock = threading.Lock()

def get_qdrant_client() -> QdrantClient:
    global _qdrant_instance
    if _qdrant_instance is not None:
        return _qdrant_instance

    with _qdrant_lock:
        if _qdrant_instance is not None:
            return _qdrant_instance
        try:
            _qdrant_instance = QdrantClient(path="./qdrant_local_data")
            return _qdrant_instance
        except Exception as e:
            logger.warning(f"Could not lock ./qdrant_local_data ({e}). Initializing in-memory fallback client.")
            _qdrant_instance = QdrantClient(location=":memory:")
            return _qdrant_instance

class LazyQdrantProxy:
    """Proxies method calls to the singleton QdrantClient."""
    def __getattr__(self, name):
        client = get_qdrant_client()
        return getattr(client, name)

qdrant = LazyQdrantProxy()

def init_vector_db():
    from app.rag.embedder import embedder
    target_dim = embedder.dimension
    
    try:
        collections = qdrant.get_collections()
        existing_names = [c.name for c in collections.collections]
        
        need_create = False
        if COLLECTION_NAME in existing_names:
            info = qdrant.get_collection(COLLECTION_NAME)
            current_size = info.config.params.vectors.size
            if current_size != target_dim:
                logger.warning(
                    f"Collection '{COLLECTION_NAME}' vector dimension mismatch: "
                    f"existing={current_size}, target={target_dim}. Recreating collection."
                )
                qdrant.delete_collection(COLLECTION_NAME)
                need_create = True
        else:
            need_create = True
            
        if need_create:
            logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}' with dim={target_dim}, distance=Cosine")
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=target_dim, distance=Distance.COSINE),
            )
            # Create payload index for user isolation
            try:
                qdrant.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="user_id",
                    field_schema=PayloadSchemaType.INTEGER,
                )
                qdrant.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="document_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as idx_err:
                logger.warning(f"Could not create payload index: {idx_err}")
                
    except Exception as e:
        logger.error(f"Error initializing Qdrant vector database: {e}")


def delete_document_vectors(document_id: str):
    try:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
        )
    except Exception as e:
        logger.error(f"Error deleting vectors for document {document_id}: {e}")

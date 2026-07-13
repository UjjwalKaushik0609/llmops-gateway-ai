"""
ChromaDB-based vector memory for RAG (Retrieval Augmented Generation).
Stores conversation history as embeddings for semantic retrieval.
"""
from typing import List, Optional, Dict, Any

import structlog

from backend.config import settings

logger = structlog.get_logger()

_chroma_client = None
_collection = None


def get_chroma():
    """Get or initialize ChromaDB client and collection."""
    global _chroma_client, _collection
    if _chroma_client is None:
        try:
            import chromadb
            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            _collection = _chroma_client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB connected", collection=settings.chroma_collection)
        except Exception as e:
            logger.warning("ChromaDB unavailable, using in-memory fallback", error=str(e))
            # Fallback: in-memory ChromaDB (no persistence)
            try:
                import chromadb
                _chroma_client = chromadb.Client()
                _collection = _chroma_client.get_or_create_collection(
                    name=settings.chroma_collection
                )
            except Exception as e2:
                logger.error("ChromaDB completely unavailable", error=str(e2))
                return None, None
    return _chroma_client, _collection


def get_embedder():
    """Get sentence transformer embedder."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning("SentenceTransformers unavailable", error=str(e))
        return None


_embedder = None


def embed_text(text: str) -> Optional[List[float]]:
    """Generate embedding for a text string."""
    global _embedder
    if _embedder is None:
        _embedder = get_embedder()
    if _embedder is None:
        return None
    try:
        return _embedder.encode(text).tolist()
    except Exception as e:
        logger.warning("Embedding failed", error=str(e))
        return None


async def store_memory(
    document_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> bool:
    """
    Store a document in the vector memory.
    Returns True on success.
    """
    _, collection = get_chroma()
    if collection is None:
        return False

    embedding = embed_text(content)
    if embedding is None:
        logger.warning("Could not embed document, skipping memory storage")
        return False

    meta = metadata or {}
    if session_id:
        meta["session_id"] = session_id
    meta["content_preview"] = content[:200]

    try:
        collection.upsert(
            ids=[document_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta],
        )
        return True
    except Exception as e:
        logger.error("Memory storage failed", error=str(e))
        return False


async def retrieve_memory(
    query: str,
    top_k: int = 5,
    session_id: Optional[str] = None,
    where: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents from vector memory.
    Returns list of {document, score, metadata} dicts.
    """
    _, collection = get_chroma()
    if collection is None:
        return []

    query_embedding = embed_text(query)
    if query_embedding is None:
        return []

    try:
        filter_dict = where or {}
        if session_id:
            filter_dict = {"session_id": {"$eq": session_id}}

        kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=min(top_k, 10),
            include=["documents", "distances", "metadatas"],
        )
        if filter_dict:
            kwargs["where"] = filter_dict

        results = collection.query(**kwargs)

        output = []
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        for doc, dist, meta in zip(docs, distances, metas):
            output.append({
                "document": doc,
                "score": round(1 - dist, 4),  # Convert distance to similarity
                "metadata": meta,
            })

        return sorted(output, key=lambda x: x["score"], reverse=True)

    except Exception as e:
        logger.error("Memory retrieval failed", error=str(e))
        return []


async def check_chroma_health() -> bool:
    """Health check for ChromaDB."""
    try:
        client, collection = get_chroma()
        if collection is None:
            return False
        collection.count()
        return True
    except Exception:
        return False

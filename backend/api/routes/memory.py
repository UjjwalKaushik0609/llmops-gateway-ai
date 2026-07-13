"""
RAG (Retrieval Augmented Generation) and Memory management endpoints.
Allows direct interaction with the vector store independent of LLM completion.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database.connection import get_db
from backend.models.db_models import User, Conversation
from backend.models.schemas import MemoryStore, RAGQuery, RAGResult
from backend.security.dependencies import get_current_user
from backend.memory.vector_store import store_memory, retrieve_memory, check_chroma_health
from backend.memory.cache import get_session_history, save_session_history

router = APIRouter(prefix="/memory", tags=["Memory & RAG"])


@router.post("/store")
async def store_document(
    payload: MemoryStore,
    current_user: User = Depends(get_current_user),
):
    """Manually store a document/fact into vector memory for later retrieval."""
    doc_id = str(uuid.uuid4())
    metadata = {**payload.metadata, "user_id": current_user.id}

    success = await store_memory(
        document_id=doc_id,
        content=payload.content,
        metadata=metadata,
        session_id=payload.session_id,
    )

    if not success:
        raise HTTPException(
            status_code=503,
            detail="Vector store unavailable. Check ChromaDB connection and sentence-transformers installation.",
        )

    return {"document_id": doc_id, "stored": True}


@router.post("/search", response_model=RAGResult)
async def search_memory(
    query: RAGQuery,
    current_user: User = Depends(get_current_user),
):
    """Semantic search over stored memory/conversation history."""
    results = await retrieve_memory(
        query=query.query,
        top_k=query.top_k,
        session_id=query.session_id,
    )

    if not results:
        return RAGResult(documents=[], scores=[], sources=[])

    return RAGResult(
        documents=[r["document"] for r in results],
        scores=[r["score"] for r in results],
        sources=[r["metadata"].get("provider", "unknown") for r in results],
    )


@router.get("/session/{session_id}/history")
async def get_session_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation history for a session (from both Redis cache and DB)."""
    # Try Redis first (fast path, recent history)
    cached_history = await get_session_history(session_id)

    # Fall back to / supplement with database records
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.asc())
    )
    db_records = result.scalars().all()

    return {
        "session_id": session_id,
        "cached_messages": cached_history,
        "persisted_turns": [
            {
                "query": r.query,
                "response": r.response,
                "created_at": r.created_at,
            }
            for r in db_records
        ],
    }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Clear cached conversation history for a session (does not delete DB records)."""
    await save_session_history(session_id, [], ttl=1)
    return {"message": f"Session {session_id} cache cleared"}


@router.get("/health")
async def memory_health():
    """Check vector store connectivity."""
    chroma_ok = await check_chroma_health()
    return {
        "chromadb": "healthy" if chroma_ok else "unavailable",
    }

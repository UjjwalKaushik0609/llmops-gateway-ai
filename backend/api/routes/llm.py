"""
Core LLM completion endpoints.
Routes requests through the multi-agent LangGraph pipeline.
"""
import inspect
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database.connection import get_db, get_db_context
from backend.models.db_models import User, Request as RequestModel, Conversation
from backend.models.schemas import LLMRequest, LLMResponse
from backend.security.dependencies import get_current_user
from backend.agents.graph import run_agent_pipeline
from backend.memory.cache import (
    check_rate_limit, make_cache_key,
    get_cached_response, set_cached_response,
    get_session_history, save_session_history,
)
from backend.memory.vector_store import store_memory
from backend.observability.metrics import record_request, record_error, record_cache_hit, record_cache_miss, record_evaluation, record_security_block
from backend.config import settings
from backend.security.user_keys import get_user_api_keys, get_user_base_urls, get_user_selected_models, get_user_routing_rules
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post("/complete", response_model=LLMResponse)
async def complete(
    request: LLMRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit check
    allowed = await check_rate_limit(current_user.id, settings.rate_limit_per_minute)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    session_id = request.session_id or str(uuid.uuid4())
    request.session_id = session_id

    # Load session history if memory is enabled
    if request.enable_memory and len(request.messages) == 1:
        history = await get_session_history(session_id)
        if history:
            from backend.models.schemas import Message
            historical = [Message(role=m["role"], content=m["content"]) for m in history]
            request.messages = historical + request.messages

    # Check cache
    if not request.stream and not request.enable_rag:
        cache_key = make_cache_key(
            request.messages,
            request.provider.value if request.provider else "auto",
            request.model or "auto"
        )
        cached = await get_cached_response(cache_key)
        if cached:
            record_cache_hit()
            cached["cached"] = True
            return LLMResponse(**cached)
        record_cache_miss()
    else:
        cache_key = None

    # Run the multi-agent pipeline
    try:
        user_api_keys = await get_user_api_keys(db, current_user.id)
        user_base_urls = await get_user_base_urls(db, current_user.id)
        user_selected_models = await get_user_selected_models(db, current_user.id)
        user_routing_rules = await get_user_routing_rules(db, current_user.id)
        pipeline_kwargs = {
            "user_api_keys": user_api_keys,
            "user_base_urls": user_base_urls,
            "user_selected_models": user_selected_models,
            "user_routing_rules": user_routing_rules,
        }
        accepted_params = inspect.signature(run_agent_pipeline).parameters
        pipeline_kwargs = {
            key: value for key, value in pipeline_kwargs.items() if key in accepted_params
        }
        response = await run_agent_pipeline(
            request,
            current_user.id,
            **pipeline_kwargs,
        )
    except HTTPException as e:
        # ── FIX: Persist blocked requests so they appear in the stream and counter ──
        if e.status_code == 400 and isinstance(e.detail, dict) and "flags" in e.detail:
            try:
                async with get_db_context() as persist_db:
                    persist_db_blocked = RequestModel(
                        user_id=current_user.id,
                        session_id=session_id,
                        provider="blocked",
                        model="security-agent",
                        tokens_input=0,
                        tokens_output=0,
                        cost_usd=0.0,
                        latency_ms=0,
                        status="blocked",
                        prompt_injection_detected=True,
                        pii_detected=any("pii:" in f for f in e.detail.get("flags", [])),
                        error_message=str(e.detail.get("flags", [])),
                        routed_by="security",
                    )
                    persist_db.add(persist_db_blocked)
                    await persist_db.flush()
                flags = e.detail.get("flags", ["unknown"])
                record_security_block(flags[0] if flags else "unknown")
            except Exception as db_err:
                logger.warning("Failed to persist blocked request", error=str(db_err))
        raise
    except Exception as e:
        logger.error("Pipeline error", error=str(e), user_id=current_user.id)
        record_error("pipeline_error", "unknown")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    # Persist request to database
    try:
        db_request = RequestModel(
            user_id=current_user.id,
            session_id=session_id,
            provider=response.provider,
            model=response.model,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            status="success",
            prompt_injection_detected=bool(response.security_flags.get("prompt_injection")),
            pii_detected=response.security_flags.get("pii_detected", False),
            routed_by=response.routing_strategy,
        )
        db.add(db_request)
        await db.flush()

        last_user_msg = next((m for m in reversed(request.messages) if m.role == "user"), None)
        if last_user_msg:
            conv = Conversation(
                user_id=current_user.id,
                request_id=db_request.id,
                session_id=session_id,
                query=last_user_msg.content,
                response=response.content,
            )
            db.add(conv)

    except Exception as e:
        logger.warning("Failed to persist request to DB", error=str(e))

    # Update session memory
    if request.enable_memory:
        all_messages = list(request.messages)
        from backend.models.schemas import Message as MsgSchema
        all_messages.append(MsgSchema(role="assistant", content=response.content))
        await save_session_history(session_id, all_messages)

    # Store in vector memory
    if request.enable_memory:
        last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
        if last_user:
            await store_memory(
                document_id=str(uuid.uuid4()),
                content=f"Q: {last_user.content}\nA: {response.content}",
                metadata={"provider": response.provider, "model": response.model},
                session_id=session_id,
            )

    # Record metrics
    record_request(
        provider=response.provider,
        model=response.model,
        status="success",
        routing_strategy=response.routing_strategy,
        latency_ms=response.latency_ms,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=response.cost_usd,
    )
    evaluation = response.metadata.get("evaluation", {})
    record_evaluation(
        provider=response.provider,
        model=response.model,
        score=evaluation.get("score"),
        skipped=evaluation.get("skipped", True),
    )

    # Cache response
    if cache_key and not request.stream:
        await set_cached_response(cache_key, response.model_dump(), ttl=1800)

    return response


@router.get("/providers")
async def list_providers(current_user: User = Depends(get_current_user)):
    from backend.router.providers import LLMProviderRegistry
    available = await LLMProviderRegistry.get_available_providers()
    all_providers = LLMProviderRegistry.list_providers()
    return {
        "providers": [
            {
                "name": p,
                "available": p in available,
                "models": LLMProviderRegistry.get_default_models(p),
                "costs": settings.provider_costs.get(p, {}),
            }
            for p in all_providers
        ]
    }


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    from backend.router.providers import LLMProviderRegistry, PROVIDER_DEFAULT_MODELS
    models = []
    for provider, model_list in PROVIDER_DEFAULT_MODELS.items():
        for model in model_list:
            costs = settings.provider_costs.get(provider, {}).get(model, {})
            models.append({
                "provider": provider,
                "model": model,
                "context_window": settings.context_windows.get(model, 8192),
                "cost_per_1m_input_usd": costs.get("input", 0),
                "cost_per_1m_output_usd": costs.get("output", 0),
            })
    return {"models": models}


@router.post("/estimate-cost")
async def estimate_cost(
    request: LLMRequest,
    current_user: User = Depends(get_current_user),
):
    from backend.router.token_utils import estimate_request_cost
    provider = request.provider.value if request.provider else settings.default_provider
    model = request.model or "gpt-4o-mini"
    estimate = estimate_request_cost(request.messages, provider, model)
    return {"provider": provider, "model": model, "estimate": estimate}
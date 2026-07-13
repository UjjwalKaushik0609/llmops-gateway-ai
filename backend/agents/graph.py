"""
LangGraph Multi-Agent Pipeline - 7 nodes:
Security → Router → Token-Opt → Memory → Executor → Evaluator → Post-process
"""
import time
import uuid
from typing import Any, Dict, List, Optional, TypedDict

import structlog
from langgraph.graph import StateGraph, END

from backend.config import settings
from backend.models.schemas import LLMRequest, LLMResponse, Message, RoutingStrategy
from backend.router.providers import LLMProviderRegistry, LLMProviderError
from backend.router.token_utils import count_message_tokens, calculate_cost, optimize_prompt, estimate_request_cost
from backend.security.auth import scan_prompt
logger = structlog.get_logger()


class AgentState(TypedDict):
    request: LLMRequest
    user_id: str
    request_id: str
    user_api_keys: Dict[str, str]
    user_base_urls: Dict[str, str]
    user_selected_models: Dict[str, str]
    user_routing_rules: List[Any]
    security_passed: bool
    security_flags: List[str]
    risk_score: float
    sanitized_messages: List[Message]
    selected_provider: str
    selected_model: str
    routing_reason: str
    optimized_messages: List[Message]
    was_compressed: bool
    estimated_cost: float
    memory_context: str
    llm_response: Optional[Dict]
    execution_error: Optional[str]
    retry_count: int
    evaluation_score: Optional[float]
    evaluation_reasoning: Optional[str]
    evaluation_skipped: bool
    final_response: Optional[LLMResponse]


def security_agent(state: AgentState) -> AgentState:
    logger.info("SecurityAgent running", request_id=state["request_id"])
    messages = state["request"].messages
    all_text = " ".join(m.content for m in messages if m.role == "user")
    result = scan_prompt(all_text)
    sanitized = []
    for msg in messages:
        if msg.role == "user":
            scan = scan_prompt(msg.content)
            sanitized.append(Message(role=msg.role, content=scan.sanitized_prompt))
        else:
            sanitized.append(msg)
    state["security_passed"] = result.is_safe
    state["security_flags"] = result.flags
    state["risk_score"] = result.risk_score
    state["sanitized_messages"] = sanitized
    return state


def router_agent(state: AgentState) -> AgentState:
    logger.info("RouterAgent running", request_id=state["request_id"])
    request = state["request"]
    messages = state["sanitized_messages"]
    print("=" * 60)
    print("Routing Strategy :", request.routing_strategy)
    print("Requested Provider:", request.provider)
    print("Requested Model   :", request.model)
    print("=" * 60)

    quality_scores = {
        "openai":     {"gpt-4o": 0.95, "gpt-4o-mini": 0.80},
        "anthropic":  {"claude-3-5-sonnet-20241022": 0.97, "claude-3-haiku-20240307": 0.78},
        "gemini":     {"gemini-2.5-pro": 0.92, "gemini-2.5-flash": 0.82},
        "mistral":    {"mistral-large-latest": 0.88, "mistral-small-latest": 0.72},
        "groq":       {"llama-3.3-70b-versatile": 0.85, "llama-3.1-8b-instant": 0.70},
        "together":   {"meta-llama/Llama-3-70b-chat-hf": 0.83},
        "openrouter": {"openai/gpt-4o-mini": 0.80},
        "ollama":     {"llama3.2": 0.70},
        "custom":     {"gpt-3.5-turbo": 0.65},
    }
    cost_scores = {
        "openai":     {"gpt-4o": 6.25, "gpt-4o-mini": 0.375},
        "anthropic":  {"claude-3-5-sonnet-20241022": 9.0, "claude-3-haiku-20240307": 0.75},
        "gemini":     {"gemini-2.5-pro": 3.125, "gemini-2.5-flash": 0.1875},
        "mistral":    {"mistral-large-latest": 4.0, "mistral-small-latest": 0.4},
        "groq":       {"llama-3.3-70b-versatile": 0.59, "llama-3.1-8b-instant": 0.05},
        "together":   {"meta-llama/Llama-3-70b-chat-hf": 0.9},
        "openrouter": {"openai/gpt-4o-mini": 0.375},
        "ollama":     {"llama3.2": 0.0},
        "custom":     {"gpt-3.5-turbo": 0.5},
    }

    # Step 1: Evaluate user routing rules
    rules = state.get("user_routing_rules", [])
    if rules:
        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        token_count = count_message_tokens(messages)
        for rule in rules:
            if not getattr(rule, "is_active", True):
                continue
            matched = False
            ctype = rule.condition_type
            cval = rule.condition_value or ""
            if ctype == "keyword":
                matched = cval.lower() in last_user_msg.lower()
            elif ctype == "token_count":
                try:
                    matched = token_count > int(cval)
                except (ValueError, TypeError):
                    pass
            elif ctype == "cost_mode":
                matched = request.routing_strategy.value == "cost"
            elif ctype == "always":
                matched = True
            if matched:
                provider = rule.target_provider
                model = rule.target_model or state.get("user_selected_models", {}).get(provider)
                state["selected_provider"] = provider
                state["selected_model"] = model or "gemini-2.5-flash"
                state["routing_reason"] = f"Custom rule '{rule.name}'"
                return state

    # Step 2: Standard routing
    strategy = request.routing_strategy

    if strategy == RoutingStrategy.manual and request.provider:
        provider = request.provider.value
        model = request.model or list(quality_scores.get(provider, {"gemini-2.5-flash": 0}).keys())[0]
        reason = f"Manual selection: {provider}/{model}"

    elif strategy == RoutingStrategy.cost:
        best = min([(p, m, c) for p, models in cost_scores.items() for m, c in models.items()], key=lambda x: x[2])
        provider, model, _ = best
        reason = "Cost optimization: cheapest available"

    elif strategy == RoutingStrategy.latency:
        fast_models = [("groq", "llama-3.1-8b-instant"), ("gemini", "gemini-2.5-flash"), ("openai", "gpt-4o-mini")]
        provider, model = fast_models[0]
        reason = "Latency optimization: fastest model"

    elif strategy == RoutingStrategy.quality:
        best = max([(p, m, q) for p, models in quality_scores.items() for m, q in models.items()], key=lambda x: x[2])
        provider, model, _ = best
        reason = "Quality optimization: best model"

    else:  # auto
        token_count = count_message_tokens(messages)
        complexity_factor = min(token_count / 1000, 1.0)
        best_score = -1
        provider, model = settings.default_provider, "gemini-2.5-flash"
        for p, models in quality_scores.items():
            for m, quality in models.items():
                cost = cost_scores.get(p, {}).get(m, 999)
                score = (quality * (0.5 + 0.5 * complexity_factor)) / (cost * 0.1 + 0.1)
                if score > best_score:
                    best_score = score
                    provider, model = p, m
        reason = f"Auto routing: balanced quality/cost (complexity={complexity_factor:.2f})"

    # Fallback: check if provider has a key (personal or server)
    user_keys = state.get("user_api_keys", {})
    provider_has_key = bool(user_keys.get(provider) or getattr(settings, f"{provider}_api_key", None))
    if not provider_has_key:
        fallback = settings.fallback_provider
        fallback_has_key = bool(user_keys.get(fallback) or getattr(settings, f"{fallback}_api_key", None))
        if fallback_has_key:
            provider = fallback
            model = list(quality_scores.get(provider, {"gemini-2.5-flash": 0}).keys())[0]
            reason += f" (fallback to {fallback})"

    print("Selected Provider:", provider)
    print("Selected Model   :", model)
    print("Reason           :", reason)
    state["selected_provider"] = provider
    state["selected_model"] = model
    state["routing_reason"] = reason
    logger.info("Route selected", provider=provider, model=model)
    return state


def token_agent(state: AgentState) -> AgentState:
    logger.info("TokenAgent running", request_id=state["request_id"])
    messages = state["sanitized_messages"]
    model = state["selected_model"]
    from backend.router.token_utils import get_context_window
    ctx_window = get_context_window(model)
    threshold = int(ctx_window * 0.8)
    optimized, compressed = optimize_prompt(messages, max_tokens=min(threshold, 8000))
    cost_estimate = estimate_request_cost(optimized, state["selected_provider"], state["selected_model"])
    state["optimized_messages"] = optimized
    state["was_compressed"] = compressed
    state["estimated_cost"] = cost_estimate["estimated_total_cost_usd"]
    return state


def memory_agent(state: AgentState) -> AgentState:
    logger.info("MemoryAgent running", request_id=state["request_id"])
    state["memory_context"] = ""
    return state


EVALUATOR_MODEL_BY_PROVIDER = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "mistral": "mistral-small-latest",
    "groq": "llama-3.1-8b-instant",
}

EVALUATOR_PROMPT_TEMPLATE = """You are a strict response-quality judge. Evaluate the ANSWER below against the ORIGINAL QUESTION.

Score faithfulness from 0.0 to 1.0:
- 1.0 = answer is fully grounded, directly addresses the question, no fabrication
- 0.5 = partially relevant or contains some unsupported claims
- 0.0 = answer is irrelevant, contradicts the question, or appears hallucinated

ORIGINAL QUESTION:
{question}

ANSWER TO EVALUATE:
{answer}

Respond with EXACTLY this format, nothing else:
SCORE: <number between 0.0 and 1.0>
REASON: <one short sentence>
"""


def _parse_evaluator_output(text: str):
    score = 0.5
    reason = "Could not parse evaluator output"
    try:
        for line in text.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                raw = line.split(":", 1)[1].strip()
                score = max(0.0, min(1.0, float(raw)))
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
    except (ValueError, IndexError):
        pass
    return score, reason


async def llm_executor_agent(state: AgentState) -> AgentState:
    logger.info("LLMExecutorAgent running", request_id=state["request_id"], provider=state["selected_provider"])
    messages = state["optimized_messages"]
    if state.get("memory_context"):
        messages = [Message(role="system", content=f"Relevant context:\n{state['memory_context']}")] + messages
    provider = state["selected_provider"]
    model = state["selected_model"]
    request = state["request"]
    retry_count = state.get("retry_count", 0)
    try:
        user_key = state.get("user_api_keys", {}).get(provider)
        user_url = state.get("user_base_urls", {}).get(provider)
        client = LLMProviderRegistry.get_client(provider, api_key=user_key, base_url=user_url)
        result = await client.complete(messages=messages, model=model, max_tokens=request.max_tokens, temperature=request.temperature)
        state["llm_response"] = result
        state["execution_error"] = None
        logger.info("LLM execution success", tokens_in=result["tokens_input"], tokens_out=result["tokens_output"], latency_ms=result["latency_ms"])
    except LLMProviderError as e:
        logger.error("LLM provider error", provider=provider, error=str(e))
        state["execution_error"] = str(e)
        state["retry_count"] = retry_count + 1
        if retry_count < 2 and provider != settings.fallback_provider:
            fallback = settings.fallback_provider
            logger.info("Retrying with fallback", fallback=fallback)
            state["selected_provider"] = fallback
            state["selected_model"] = "gemini-2.5-flash"
            return await llm_executor_agent(state)
    except Exception as e:
        logger.error("Unexpected error in LLM executor", error=str(e))
        state["execution_error"] = f"Unexpected error: {str(e)}"
    return state


async def evaluator_agent(state: AgentState) -> AgentState:
    logger.info("EvaluatorAgent running", request_id=state["request_id"])
    if state.get("execution_error") and not state.get("llm_response"):
        state["evaluation_skipped"] = True
        return state
    result = state["llm_response"]
    question = next((m.content for m in reversed(state["request"].messages) if m.role == "user"), "")
    answer = result.get("content", "") if result else ""
    if not answer or not question:
        state["evaluation_skipped"] = True
        return state
    provider = state["selected_provider"]
    judge_model = EVALUATOR_MODEL_BY_PROVIDER.get(provider, "gemini-2.5-flash")
    judge_provider = provider if provider in EVALUATOR_MODEL_BY_PROVIDER else "gemini"
    prompt = EVALUATOR_PROMPT_TEMPLATE.format(question=question[:2000], answer=answer[:2000])
    try:
        user_key = state.get("user_api_keys", {}).get(judge_provider)
        user_url = state.get("user_base_urls", {}).get(judge_provider)
        client = LLMProviderRegistry.get_client(judge_provider, api_key=user_key, base_url=user_url)
        judge_result = await client.complete(messages=[Message(role="user", content=prompt)], model=judge_model, max_tokens=100, temperature=0.0)
        score, reason = _parse_evaluator_output(judge_result["content"])
        state["evaluation_score"] = score
        state["evaluation_reasoning"] = reason
        state["evaluation_skipped"] = False
        logger.info("Evaluation complete", score=score)
    except Exception as e:
        logger.warning("Evaluator agent failed, skipping", error=str(e))
        state["evaluation_score"] = None
        state["evaluation_reasoning"] = None
        state["evaluation_skipped"] = True
    return state


def post_process_agent(state: AgentState) -> AgentState:
    logger.info("PostProcessAgent running", request_id=state["request_id"])
    if state.get("execution_error") and not state.get("llm_response"):
        state["final_response"] = None
        return state
    result = state["llm_response"]
    actual_cost = calculate_cost(state["selected_provider"], state["selected_model"], result["tokens_input"], result["tokens_output"])
    from datetime import datetime
    final = LLMResponse(
        request_id=state["request_id"],
        session_id=state["request"].session_id or str(uuid.uuid4()),
        provider=state["selected_provider"],
        model=state["selected_model"],
        content=result["content"],
        tokens_input=result["tokens_input"],
        tokens_output=result["tokens_output"],
        cost_usd=actual_cost,
        latency_ms=result["latency_ms"],
        routing_strategy=state["request"].routing_strategy.value,
        cached=False,
        security_flags={
            "prompt_injection": state.get("security_flags", []),
            "risk_score": state.get("risk_score", 0.0),
            "pii_detected": any("pii:" in f for f in state.get("security_flags", [])),
        },
        metadata={
            "routing_reason": state.get("routing_reason"),
            "was_compressed": state.get("was_compressed", False),
            "estimated_cost": state.get("estimated_cost", 0),
            "evaluation": {
                "score": state.get("evaluation_score"),
                "reasoning": state.get("evaluation_reasoning"),
                "skipped": state.get("evaluation_skipped", True),
            },
        },
        timestamp=datetime.utcnow(),
    )
    state["final_response"] = final
    return state


def check_security(state: AgentState) -> str:
    return "proceed" if state.get("security_passed", True) else "blocked"


def check_execution(state: AgentState) -> str:
    return "failed" if (state.get("execution_error") and not state.get("llm_response")) else "success"


def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    workflow.add_node("security", security_agent)
    workflow.add_node("router", router_agent)
    workflow.add_node("token_optimizer", token_agent)
    workflow.add_node("memory", memory_agent)
    workflow.add_node("executor", llm_executor_agent)
    workflow.add_node("evaluator", evaluator_agent)
    workflow.add_node("post_process", post_process_agent)
    workflow.set_entry_point("security")
    workflow.add_conditional_edges("security", check_security, {"blocked": END, "proceed": "router"})
    workflow.add_edge("router", "token_optimizer")
    workflow.add_edge("token_optimizer", "memory")
    workflow.add_edge("memory", "executor")
    workflow.add_conditional_edges("executor", check_execution, {"failed": "post_process", "success": "evaluator"})
    workflow.add_edge("evaluator", "post_process")
    workflow.add_edge("post_process", END)
    return workflow.compile()


agent_graph = build_agent_graph()


async def run_agent_pipeline(
    request: LLMRequest,
    user_id: str,
    user_api_keys: Optional[Dict[str, str]] = None,
    user_base_urls: Optional[Dict[str, str]] = None,
    user_selected_models: Optional[Dict[str, str]] = None,
    user_routing_rules: Optional[List[Any]] = None,
) -> LLMResponse:
    request_id = str(uuid.uuid4())
    initial_state: AgentState = {
        "request": request,
        "user_id": user_id,
        "request_id": request_id,
        "user_api_keys": user_api_keys or {},
        "user_base_urls": user_base_urls or {},
        "user_selected_models": user_selected_models or {},
        "user_routing_rules": user_routing_rules or [],
        "security_passed": True,
        "security_flags": [],
        "risk_score": 0.0,
        "sanitized_messages": request.messages,
        "selected_provider": settings.default_provider,
        "selected_model": "gemini-2.5-flash",
        "routing_reason": "",
        "optimized_messages": request.messages,
        "was_compressed": False,
        "estimated_cost": 0.0,
        "memory_context": "",
        "llm_response": None,
        "execution_error": None,
        "retry_count": 0,
        "evaluation_score": None,
        "evaluation_reasoning": None,
        "evaluation_skipped": True,
        "final_response": None,
    }
    final_state = await agent_graph.ainvoke(initial_state)
    if not final_state.get("security_passed"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail={
            "error": "Request blocked by security agent",
            "flags": final_state.get("security_flags", []),
            "risk_score": final_state.get("risk_score", 0),
        })
    if not final_state.get("final_response"):
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"LLM execution failed: {final_state.get('execution_error', 'Unknown error')}")
    return final_state["final_response"]
"""
Token counting, cost estimation, and prompt optimization utilities.
"""
from typing import List, Dict, Optional, Tuple
from backend.config import settings
from backend.models.schemas import Message
import structlog

logger = structlog.get_logger()


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count without tiktoken.
    Rule of thumb: ~4 characters per token for English text.
    """
    return max(1, len(text) // 4)


def count_tokens_tiktoken(text: str, model: str = "gpt-4o") -> int:
    """Count tokens using tiktoken (OpenAI's tokenizer), falling back to approximation
    if tiktoken is unavailable or its encoding files can't be fetched (e.g. offline)."""
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception as e:
        logger.debug("tiktoken unavailable, using approximation", error=str(e))
        return count_tokens_approx(text)


def count_message_tokens(messages: List[Message], model: str = "gpt-4o") -> int:
    """Count total tokens in a list of messages."""
    total = 0
    for msg in messages:
        total += count_tokens_tiktoken(msg.content, model)
        total += 4  # overhead per message (role, separators)
    return total + 3  # reply priming


def calculate_cost(
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
) -> float:
    """Calculate USD cost for a request."""
    provider_costs = settings.provider_costs
    if provider not in provider_costs:
        logger.warning("Unknown provider for cost calculation", provider=provider)
        return 0.0

    model_costs = provider_costs[provider]

    # Find matching model (partial match for flexibility)
    matched_model = None
    for m in model_costs:
        if m in model or model in m:
            matched_model = m
            break

    if not matched_model:
        # Use cheapest model for that provider as fallback
        matched_model = list(model_costs.keys())[-1]
        logger.debug("Using fallback model cost", provider=provider, model=matched_model)

    costs = model_costs[matched_model]
    input_cost = (tokens_input / 1_000_000) * costs["input"]
    output_cost = (tokens_output / 1_000_000) * costs["output"]
    return round(input_cost + output_cost, 8)


def get_context_window(model: str) -> int:
    """Get context window size for a model."""
    windows = settings.context_windows
    for m, size in windows.items():
        if m in model or model in m:
            return size
    return 8192  # conservative default


def optimize_prompt(messages: List[Message], max_tokens: int = 3000) -> Tuple[List[Message], bool]:
    """
    Compress conversation history if it's approaching the token limit.
    Returns (optimized_messages, was_compressed).
    """
    total_tokens = count_message_tokens(messages)

    if total_tokens <= max_tokens:
        return messages, False

    logger.info("Compressing conversation", original_tokens=total_tokens, target=max_tokens)

    # Strategy: Keep system message + last 3 exchanges + summarize the rest
    system_msgs = [m for m in messages if m.role == "system"]
    conversation = [m for m in messages if m.role != "system"]

    # Always keep the last 6 messages (3 user-assistant pairs)
    recent = conversation[-6:] if len(conversation) > 6 else conversation
    older = conversation[:-6] if len(conversation) > 6 else []

    if older:
        # Create a summary of older messages
        summary_content = "Previous conversation summary:\n"
        for msg in older:
            role = "User" if msg.role == "user" else "Assistant"
            # Take first 100 chars of each message for summary
            summary_content += f"{role}: {msg.content[:100]}...\n"

        summary_msg = Message(role="user", content=summary_content)
        optimized = system_msgs + [summary_msg] + recent
    else:
        optimized = system_msgs + recent

    new_total = count_message_tokens(optimized)
    logger.info("Compression complete", original=total_tokens, compressed=new_total)
    return optimized, True


def estimate_request_cost(
    messages: List[Message],
    provider: str,
    model: str,
    expected_output_tokens: int = 500,
) -> Dict[str, float]:
    """
    Estimate cost before making a request.
    Returns breakdown of estimated costs.
    """
    input_tokens = count_message_tokens(messages, model)
    input_cost = calculate_cost(provider, model, input_tokens, 0)
    output_cost = calculate_cost(provider, model, 0, expected_output_tokens)
    return {
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": expected_output_tokens,
        "estimated_input_cost_usd": input_cost,
        "estimated_output_cost_usd": output_cost,
        "estimated_total_cost_usd": round(input_cost + output_cost, 8),
    }

"""
Prometheus metrics for LLMOps Gateway AI.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

REQUEST_COUNT = Counter("llmops_requests_total", "Total LLM requests", ["provider", "model", "status", "routing_strategy"])
REQUEST_LATENCY = Histogram("llmops_request_latency_seconds", "LLM request latency", ["provider", "model"], buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0])
TOKENS_TOTAL = Counter("llmops_tokens_total", "Total tokens processed", ["provider", "direction"])
TOKEN_OPTIMIZATION_SAVINGS = Counter("llmops_token_optimization_savings_total", "Tokens saved by compression", ["provider"])
COST_USD = Counter("llmops_cost_usd_total", "Total USD cost", ["provider", "model"])
COST_GAUGE = Gauge("llmops_current_hour_cost_usd", "Cost in current hour (USD)", ["provider"])
SECURITY_BLOCKS = Counter("llmops_security_blocks_total", "Requests blocked by security agent", ["reason"])
CACHE_HITS = Counter("llmops_cache_hits_total", "Cache hits")
CACHE_MISSES = Counter("llmops_cache_misses_total", "Cache misses")
ACTIVE_SESSIONS = Gauge("llmops_active_sessions", "Number of active sessions")
PROVIDER_UP = Gauge("llmops_provider_up", "Provider availability (1=up, 0=down)", ["provider"])
ERRORS = Counter("llmops_errors_total", "Total errors", ["error_type", "provider"])
EVALUATION_SCORE = Histogram("llmops_evaluation_score", "Evaluator faithfulness scores (0-1)", ["provider", "model"], buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0])
EVALUATION_SKIPPED = Counter("llmops_evaluation_skipped_total", "Times evaluator was skipped")


def record_request(provider, model, status, routing_strategy, latency_ms, tokens_input, tokens_output, cost_usd):
    REQUEST_COUNT.labels(provider=provider, model=model, status=status, routing_strategy=routing_strategy).inc()
    REQUEST_LATENCY.labels(provider=provider, model=model).observe(latency_ms / 1000)
    TOKENS_TOTAL.labels(provider=provider, direction="input").inc(tokens_input)
    TOKENS_TOTAL.labels(provider=provider, direction="output").inc(tokens_output)
    COST_USD.labels(provider=provider, model=model).inc(cost_usd)


def record_security_block(reason: str):
    SECURITY_BLOCKS.labels(reason=reason).inc()


def record_cache_hit():
    CACHE_HITS.inc()


def record_cache_miss():
    CACHE_MISSES.inc()


def set_provider_status(provider: str, is_up: bool):
    PROVIDER_UP.labels(provider=provider).set(1 if is_up else 0)


def record_error(error_type: str, provider: str = "unknown"):
    ERRORS.labels(error_type=error_type, provider=provider).inc()


def record_evaluation(provider: str, model: str, score: float = None, skipped: bool = False):
    if skipped or score is None:
        EVALUATION_SKIPPED.inc()
    else:
        EVALUATION_SCORE.labels(provider=provider, model=model).observe(score)


async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

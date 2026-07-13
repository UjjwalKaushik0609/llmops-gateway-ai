"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, validator
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class RoutingStrategy(str, enum.Enum):
    auto = "auto"          # LangGraph agent decides
    cost = "cost"          # Cheapest provider
    latency = "latency"    # Fastest provider
    quality = "quality"    # Best quality provider
    manual = "manual"      # User specifies provider


class LLMProvider(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    mistral = "mistral"
    grok = "grok"


# ─── Auth Schemas ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Optional[str] = "user"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    daily_token_limit: int
    monthly_budget_usd: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─── LLM Request/Response Schemas ─────────────────────────────────────────────

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class LLMRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None
    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    routing_strategy: RoutingStrategy = RoutingStrategy.auto
    max_tokens: int = Field(default=2048, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False
    enable_rag: bool = False
    enable_memory: bool = True
    metadata: Dict[str, Any] = {}


class LLMResponse(BaseModel):
    request_id: str
    session_id: str
    provider: str
    model: str
    content: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    routing_strategy: str
    cached: bool = False
    security_flags: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    timestamp: datetime


class StreamChunk(BaseModel):
    request_id: str
    delta: str
    finished: bool = False


# ─── API Key Schemas ───────────────────────────────────────────────────────────

class APIKeyCreate(BaseModel):
    provider: LLMProvider
    key_name: str = Field(..., min_length=2, max_length=255)
    api_key: str = Field(..., min_length=10)
    monthly_quota_usd: float = Field(default=500.0, ge=0)


class APIKeyResponse(BaseModel):
    id: str
    provider: str
    key_name: str
    status: str
    monthly_quota_usd: float
    current_month_spend: float
    last_rotated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Analytics Schemas ─────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    requests_by_provider: Dict[str, int]
    cost_by_provider: Dict[str, float]
    error_rate: float
    top_models: List[Dict[str, Any]]
    daily_costs: List[Dict[str, Any]]


class CostForecast(BaseModel):
    current_month_spend: float
    projected_month_spend: float
    daily_average: float
    days_remaining: int
    budget_remaining: float
    will_exceed_budget: bool
    recommended_actions: List[str]


# ─── Memory/RAG Schemas ────────────────────────────────────────────────────────

class MemoryStore(BaseModel):
    session_id: str
    content: str
    metadata: Dict[str, Any] = {}


class RAGQuery(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None


class RAGResult(BaseModel):
    documents: List[str]
    scores: List[float]
    sources: List[str]


# ─── Security Schemas ──────────────────────────────────────────────────────────

class SecurityScanResult(BaseModel):
    is_safe: bool
    prompt_injection_detected: bool
    pii_detected: bool
    sensitive_data_detected: bool
    sanitized_prompt: str
    flags: List[str]
    risk_score: float  # 0.0 (safe) to 1.0 (dangerous)


# ─── Health Check ──────────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    status: str
    version: str
    services: Dict[str, str]
    timestamp: datetime

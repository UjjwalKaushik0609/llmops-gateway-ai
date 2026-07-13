"""
SQLAlchemy ORM Models for LLMOps Gateway AI.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


class ProviderStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    rate_limited = "rate_limited"
    error = "error"


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    daily_token_limit = Column(Integer, default=1_000_000)
    monthly_budget_usd = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    key_name = Column(String(255), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    monthly_quota_usd = Column(Float, default=500.0)
    current_month_spend = Column(Float, default=0.0)
    status = Column(SAEnum(ProviderStatus), default=ProviderStatus.active)
    last_rotated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="api_keys")


class Request(Base):
    __tablename__ = "requests"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(50), default="success")
    error_message = Column(Text, nullable=True)
    prompt_injection_detected = Column(Boolean, default=False)
    pii_detected = Column(Boolean, default=False)
    routed_by = Column(String(50), default="manual")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("User", back_populates="requests")
    conversation = relationship("Conversation", back_populates="request", uselist=False)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    request_id = Column(String(36), ForeignKey("requests.id"), nullable=True)
    session_id = Column(String(255), nullable=False, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    embedding_id = Column(String(255), nullable=True)
    extra_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="conversations")
    request = relationship("Request", back_populates="conversation")


class ProviderConfig(Base):
    __tablename__ = "provider_configs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    encrypted_key = Column(Text, nullable=True)
    base_url = Column(String(500), nullable=True)
    selected_model = Column(String(200), nullable=True)
    last_connected_at = Column(DateTime, nullable=True)
    last_latency_ms = Column(Integer, nullable=True)
    health_status = Column(String(20), default="unknown")
    health_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", backref="provider_configs")


class RouterRule(Base):
    __tablename__ = "router_rules"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    priority = Column(Integer, default=0)
    name = Column(String(255), nullable=False)
    condition_type = Column(String(50), nullable=False)
    condition_value = Column(String(500), nullable=True)
    target_provider = Column(String(50), nullable=False)
    target_model = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="router_rules")


class SetupWizardState(Base):
    __tablename__ = "setup_wizard_states"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    env_migrated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="setup_wizard_state", uselist=False)


class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    metric_name = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(JSON, default={})
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    rule_name = Column(String(255), nullable=False)
    metric = Column(String(100), nullable=False)
    threshold = Column(Float, nullable=False)
    operator = Column(String(10), nullable=False)
    notification_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
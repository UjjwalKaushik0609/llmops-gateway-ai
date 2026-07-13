"""
Provider Settings API - all 11 spec requirements.
"""
import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from backend.database.connection import get_db
from backend.models.db_models import ProviderConfig, RouterRule, SetupWizardState, User
from backend.security.auth import encrypt_api_key, decrypt_api_key
from backend.security.dependencies import get_current_user
from backend.router.providers import LLMProviderRegistry, PROVIDER_DEFAULT_MODELS
from backend.models.schemas import Message
from backend.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/providers", tags=["Provider Settings"])


class ProviderSaveRequest(BaseModel):
    provider: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    selected_model: Optional[str] = None


class ProviderResponse(BaseModel):
    provider: str
    enabled: bool
    has_key: bool
    masked_key: Optional[str]
    base_url: Optional[str]
    selected_model: Optional[str]
    available_models: List[str]
    last_connected_at: Optional[datetime]
    last_latency_ms: Optional[int]
    health_status: str
    health_message: Optional[str]


class TestConnectionResponse(BaseModel):
    provider: str
    connected: bool
    latency_ms: Optional[int]
    available_models: List[str]
    error: Optional[str]


class RouterRuleCreate(BaseModel):
    name: str
    priority: int = 0
    condition_type: str
    condition_value: Optional[str] = None
    target_provider: str
    target_model: Optional[str] = None
    is_active: bool = True


class RouterRuleResponse(BaseModel):
    id: str
    name: str
    priority: int
    condition_type: str
    condition_value: Optional[str]
    target_provider: str
    target_model: Optional[str]
    is_active: bool


class SetupWizardCompleteRequest(BaseModel):
    providers: List[ProviderSaveRequest]


class MigrateEnvRequest(BaseModel):
    confirm: bool = True


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "*" * (len(key) - 6) + key[-2:]


async def _get_provider_config(db, user_id, provider):
    result = await db.execute(
        select(ProviderConfig).where(and_(ProviderConfig.user_id == user_id, ProviderConfig.provider == provider))
    )
    return result.scalar_one_or_none()


async def _resolve_user_key_and_url(db, user_id, provider):
    config = await _get_provider_config(db, user_id, provider)
    api_key = None
    base_url = None
    if config:
        base_url = config.base_url
        if config.encrypted_key:
            try:
                api_key = decrypt_api_key(config.encrypted_key)
            except Exception:
                pass
    return api_key, base_url


@router.get("/", response_model=List[ProviderResponse])
async def list_providers(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == current_user.id))
    configs = {c.provider: c for c in result.scalars().all()}
    env_keys = {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "gemini": settings.gemini_api_key,
        "mistral": settings.mistral_api_key,
    }
    providers = []
    for provider in LLMProviderRegistry.list_providers():
        config = configs.get(provider)
        has_personal_key = config and bool(config.encrypted_key)
        has_env_key = bool(env_keys.get(provider))
        has_key = has_personal_key or has_env_key
        masked = None
        if has_personal_key:
            try:
                raw = decrypt_api_key(config.encrypted_key)
                masked = mask_key(raw)
            except Exception:
                masked = "****"
        elif has_env_key:
            masked = mask_key(env_keys[provider])
        providers.append(ProviderResponse(
            provider=provider,
            enabled=config.enabled if config else True,
            has_key=has_key,
            masked_key=masked,
            base_url=config.base_url if config else None,
            selected_model=config.selected_model if config else (PROVIDER_DEFAULT_MODELS.get(provider, [""])[0] if PROVIDER_DEFAULT_MODELS.get(provider) else ""),
            available_models=PROVIDER_DEFAULT_MODELS.get(provider, []),
            last_connected_at=config.last_connected_at if config else None,
            last_latency_ms=config.last_latency_ms if config else None,
            health_status=config.health_status if config else "unknown",
            health_message=config.health_message if config else None,
        ))
    return providers


@router.post("/save")
async def save_provider(payload: ProviderSaveRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.provider not in LLMProviderRegistry.list_providers():
        raise HTTPException(status_code=400, detail=f"Unknown provider: {payload.provider}")
    config = await _get_provider_config(db, current_user.id, payload.provider)
    if not config:
        config = ProviderConfig(user_id=current_user.id, provider=payload.provider)
        db.add(config)
    config.enabled = payload.enabled
    config.base_url = payload.base_url
    config.selected_model = payload.selected_model
    if payload.api_key:
        config.encrypted_key = encrypt_api_key(payload.api_key)
        config.health_status = "unknown"
    await db.flush()
    return {"message": f"{payload.provider} configuration saved"}


@router.delete("/{provider}")
async def delete_provider_key(provider: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_provider_config(db, current_user.id, provider)
    if config:
        config.encrypted_key = None
        config.health_status = "unknown"
        config.health_message = "Key removed"
    return {"message": f"API key for {provider} deleted"}


@router.post("/test/{provider}", response_model=TestConnectionResponse)
async def test_connection(provider: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if provider not in LLMProviderRegistry.list_providers():
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    api_key, base_url = await _resolve_user_key_and_url(db, current_user.id, provider)
    if not api_key:
        env_key_map = {"openai": settings.openai_api_key, "anthropic": settings.anthropic_api_key, "gemini": settings.gemini_api_key, "mistral": settings.mistral_api_key}
        api_key = env_key_map.get(provider)
    start = time.time()
    error_msg = None
    connected = False
    latency_ms = None
    try:
        client = LLMProviderRegistry.get_client(provider, api_key=api_key, base_url=base_url)
        available = await client.is_available()
        if not available:
            raise Exception("No API key configured for this provider")
        test_result = await client.complete(
            messages=[Message(role="user", content="Reply with just: OK")],
            max_tokens=10, temperature=0.0,
        )
        latency_ms = test_result["latency_ms"]
        connected = True
    except Exception as e:
        error_msg = str(e)
        latency_ms = int((time.time() - start) * 1000)
    config = await _get_provider_config(db, current_user.id, provider)
    if not config:
        config = ProviderConfig(user_id=current_user.id, provider=provider)
        db.add(config)
    config.health_status = "healthy" if connected else "error"
    config.health_message = None if connected else error_msg
    config.last_latency_ms = latency_ms
    if connected:
        config.last_connected_at = datetime.utcnow()
    await db.flush()
    return TestConnectionResponse(provider=provider, connected=connected, latency_ms=latency_ms, available_models=PROVIDER_DEFAULT_MODELS.get(provider, []), error=error_msg)


@router.get("/rules", response_model=List[RouterRuleResponse])
async def list_routing_rules(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RouterRule).where(RouterRule.user_id == current_user.id).order_by(RouterRule.priority))
    return [RouterRuleResponse(id=r.id, name=r.name, priority=r.priority, condition_type=r.condition_type, condition_value=r.condition_value, target_provider=r.target_provider, target_model=r.target_model, is_active=r.is_active) for r in result.scalars().all()]


@router.post("/rules", status_code=201)
async def create_routing_rule(rule: RouterRuleCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_rule = RouterRule(user_id=current_user.id, name=rule.name, priority=rule.priority, condition_type=rule.condition_type, condition_value=rule.condition_value, target_provider=rule.target_provider, target_model=rule.target_model, is_active=rule.is_active)
    db.add(db_rule)
    await db.flush()
    return {"message": "Routing rule created", "id": db_rule.id}


@router.delete("/rules/{rule_id}")
async def delete_routing_rule(rule_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RouterRule).where(and_(RouterRule.id == rule_id, RouterRule.user_id == current_user.id)))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    return {"message": "Rule deleted"}


@router.get("/setup/status")
async def get_setup_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SetupWizardState).where(SetupWizardState.user_id == current_user.id))
    state = result.scalar_one_or_none()
    return {"completed": state.completed if state else False, "env_migrated": state.env_migrated if state else False}


@router.post("/setup/complete")
async def complete_setup_wizard(payload: SetupWizardCompleteRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for p in payload.providers:
        config = await _get_provider_config(db, current_user.id, p.provider)
        if not config:
            config = ProviderConfig(user_id=current_user.id, provider=p.provider)
            db.add(config)
        config.enabled = p.enabled
        config.base_url = p.base_url
        config.selected_model = p.selected_model
        if p.api_key:
            config.encrypted_key = encrypt_api_key(p.api_key)
    result = await db.execute(select(SetupWizardState).where(SetupWizardState.user_id == current_user.id))
    wizard = result.scalar_one_or_none()
    if not wizard:
        wizard = SetupWizardState(user_id=current_user.id)
        db.add(wizard)
    wizard.completed = True
    wizard.completed_at = datetime.utcnow()
    await db.flush()
    return {"message": "Setup complete"}


@router.post("/setup/migrate-env")
async def migrate_env_keys(payload: MigrateEnvRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not payload.confirm:
        return {"message": "Pass confirm=true to proceed"}
    env_keys = {"openai": settings.openai_api_key, "anthropic": settings.anthropic_api_key, "gemini": settings.gemini_api_key, "mistral": settings.mistral_api_key}
    migrated = []
    for provider, key in env_keys.items():
        if not key:
            continue
        config = await _get_provider_config(db, current_user.id, provider)
        if config and config.encrypted_key:
            continue
        if not config:
            config = ProviderConfig(user_id=current_user.id, provider=provider)
            db.add(config)
        config.encrypted_key = encrypt_api_key(key)
        config.health_status = "unknown"
        migrated.append(provider)
    result = await db.execute(select(SetupWizardState).where(SetupWizardState.user_id == current_user.id))
    wizard = result.scalar_one_or_none()
    if not wizard:
        wizard = SetupWizardState(user_id=current_user.id)
        db.add(wizard)
    wizard.env_migrated = True
    await db.flush()
    return {"migrated": migrated, "message": f"Imported {len(migrated)} key(s) from .env into secure storage"}
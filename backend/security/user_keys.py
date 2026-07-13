"""
Resolves a user's personal LLM provider API keys and base URLs from the database.
"""
from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.db_models import APIKey, ProviderConfig, ProviderStatus
from backend.security.auth import decrypt_api_key
import structlog
logger = structlog.get_logger()


async def get_user_api_keys(db: AsyncSession, user_id: str) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.user_id == user_id, ProviderConfig.enabled == True)
    )
    for row in result.scalars().all():
        if row.encrypted_key:
            try:
                keys[row.provider] = decrypt_api_key(row.encrypted_key)
            except Exception as e:
                logger.warning("Failed to decrypt ProviderConfig key", provider=row.provider, error=str(e))
    result2 = await db.execute(
        select(APIKey).where(APIKey.user_id == user_id, APIKey.status == ProviderStatus.active)
    )
    for row in result2.scalars().all():
        if row.provider not in keys:
            try:
                keys[row.provider] = decrypt_api_key(row.encrypted_key)
            except Exception as e:
                logger.warning("Failed to decrypt APIKey", provider=row.provider, error=str(e))
    return keys


async def get_user_base_urls(db: AsyncSession, user_id: str) -> Dict[str, str]:
    urls: Dict[str, str] = {}
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.user_id == user_id, ProviderConfig.base_url != None)
    )
    for row in result.scalars().all():
        if row.base_url:
            urls[row.provider] = row.base_url
    return urls


async def get_user_selected_models(db: AsyncSession, user_id: str) -> Dict[str, str]:
    models: Dict[str, str] = {}
    result = await db.execute(select(ProviderConfig).where(ProviderConfig.user_id == user_id))
    for row in result.scalars().all():
        if row.selected_model:
            models[row.provider] = row.selected_model
    return models


async def get_user_routing_rules(db: AsyncSession, user_id: str):
    from backend.models.db_models import RouterRule
    result = await db.execute(
        select(RouterRule).where(RouterRule.user_id == user_id, RouterRule.is_active == True).order_by(RouterRule.priority)
    )
    return result.scalars().all()
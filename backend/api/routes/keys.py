"""
API Key management: add, list, rotate, delete provider API keys.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database.connection import get_db
from backend.models.db_models import APIKey, User
from backend.models.schemas import APIKeyCreate, APIKeyResponse
from backend.security.auth import encrypt_api_key, decrypt_api_key
from backend.security.dependencies import get_current_user

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("/", response_model=APIKeyResponse, status_code=201)
async def add_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new LLM provider API key (stored encrypted)."""
    api_key = APIKey(
        user_id=current_user.id,
        provider=key_data.provider.value,
        key_name=key_data.key_name,
        encrypted_key=encrypt_api_key(key_data.api_key),
        monthly_quota_usd=key_data.monthly_quota_usd,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return api_key


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user (keys are masked)."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    return result.scalars().all()


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(key)
    return {"message": "API key deleted successfully"}


@router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    new_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rotate (replace) an existing API key."""
    from datetime import datetime
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.encrypted_key = encrypt_api_key(new_key)
    key.last_rotated_at = datetime.utcnow()
    key.status = "active"
    return {"message": "API key rotated successfully", "rotated_at": key.last_rotated_at}

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.limiter import OptionalRateLimiter
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyPublic, APIKeyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.post("", response_model=APIKeyResponse, status_code=201, dependencies=[Depends(OptionalRateLimiter(times=10, seconds=60))])
def create_api_key(
    payload: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new API key for a service. Store the returned key — it won't be shown again."""
    api_key = APIKey(
        key=APIKey.generate(),
        user_id=current_user.id,
        service_name=payload.service_name,
        description=payload.description,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    logger.info("Created API key for user=%s service=%s id=%s", current_user.id, api_key.service_name, api_key.id)
    return api_key


@router.get("", response_model=List[APIKeyPublic])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active API keys for the current user."""
    return (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id, APIKey.is_active == True)  # noqa: E712
        .all()
    )


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate an API key by ID (must belong to the current user)."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == current_user.id
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    db.commit()
    logger.info("Revoked API key id=%s user=%s", key_id, current_user.id)

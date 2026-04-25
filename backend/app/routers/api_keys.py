import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyPublic, APIKeyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.post("", response_model=APIKeyResponse, status_code=201)
def create_api_key(payload: APIKeyCreate, db: Session = Depends(get_db)):
    """Generate a new API key for a service. Store the returned key — it won't be shown again."""
    api_key = APIKey(
        key=APIKey.generate(),
        service_name=payload.service_name,
        description=payload.description,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    logger.info("Created API key for service=%s id=%s", api_key.service_name, api_key.id)
    return api_key


@router.get("", response_model=List[APIKeyPublic])
def list_api_keys(db: Session = Depends(get_db)):
    """List all active API keys (keys themselves are not returned)."""
    return db.query(APIKey).filter(APIKey.is_active == True).all()  # noqa: E712


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(key_id: int, db: Session = Depends(get_db)):
    """Deactivate an API key by ID."""
    api_key = db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    db.commit()
    logger.info("Revoked API key id=%s service=%s", key_id, api_key.service_name)

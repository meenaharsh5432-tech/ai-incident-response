from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)


class APIKeyResponse(BaseModel):
    id: int
    key: str          # shown ONLY at creation time
    service_name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyPublic(BaseModel):
    """Safe list view — never exposes the raw key."""
    id: int
    service_name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

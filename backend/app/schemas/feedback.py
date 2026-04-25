from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    was_helpful: bool
    actual_fix: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    incident_id: int
    was_helpful: bool
    actual_fix: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Environment(str, Enum):
    prod = "prod"
    staging = "staging"
    dev = "dev"


class ErrorIngest(BaseModel):
    error_type: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    stack_trace: Optional[str] = None
    service_name: str = Field(..., min_length=1, max_length=100)
    environment: Environment = Environment.prod
    metadata: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    id: int
    incident_id: int
    error_type: str
    service_name: str
    environment: str
    created_at: datetime
    is_new_incident: bool

    model_config = {"from_attributes": True}


class ErrorDetail(BaseModel):
    id: int
    message: str
    stack_trace: Optional[str] = None
    error_type: str
    service_name: str
    environment: str
    metadata_: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ErrorBatchIngest(BaseModel):
    errors: List[ErrorIngest] = Field(..., min_length=1, max_length=100)


class BatchErrorResponse(BaseModel):
    processed: int
    deduplicated: int
    results: List[ErrorResponse]

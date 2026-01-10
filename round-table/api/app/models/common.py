"""Common Pydantic models used across the API"""

import secrets
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    return f"{prefix}_{secrets.token_hex(5)}"


class Metadata(BaseModel):
    """Response metadata"""
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(ge=1, default=1)
    per_page: int = Field(ge=1, le=100, default=20)
    total_count: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool = False
    has_prev: bool = False


class SuccessResponse(BaseModel):
    """Standard success response wrapper"""
    success: bool = True
    data: Any
    meta: Optional[Metadata] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""
    success: bool = False
    error: ErrorDetail
    meta: Optional[Metadata] = None

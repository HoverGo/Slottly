from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyRatingSummary(BaseModel):
    average: float
    count: int


class PublicReviewCreate(BaseModel):
    client_phone: str = Field(min_length=5, max_length=50)
    client_name: str | None = Field(default=None, max_length=255)
    member_id: UUID | None = Field(default=None, description="Мастер, к которому ходил клиент")
    rating: int = Field(ge=1, le=5, description="Оценка компании")
    text: str = Field(min_length=10, max_length=2000, description="Текст отзыва")


class PublicReviewResponse(BaseModel):
    id: UUID
    rating: int
    text: str
    client_name: str | None
    member_id: UUID | None
    member_name: str | None
    created_at: Any


class PublicReviewListResponse(BaseModel):
    rating: CompanyRatingSummary
    reviews: list[PublicReviewResponse]


class VisitMemberOptionResponse(BaseModel):
    id: UUID
    full_name: str
    photo_url: str | None = None


class CompanyReviewResponse(BaseModel):
    id: UUID
    company_id: UUID
    client_id: UUID
    client_name: str | None
    member_id: UUID | None
    member_name: str | None
    rating: int
    text: str
    is_visible: bool
    created_at: Any


class CompanyReviewsPageResponse(BaseModel):
    rating: CompanyRatingSummary
    reviews: list[CompanyReviewResponse]

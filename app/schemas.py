from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


# --- Autocomplete ---


class LatLng(BaseModel):
    latitude: float
    longitude: float


class Viewport(BaseModel):
    low: LatLng
    high: LatLng


class AutocompleteItem(BaseModel):
    description: str
    place_id: str
    viewport: Viewport | None = None


class AutocompleteResponse(BaseModel):
    predictions: list[AutocompleteItem]


# --- Lead Generation ---


class Bounds(BaseModel):
    low: LatLng
    high: LatLng


class GenerateLeadsRequest(BaseModel):
    sector: str = Field(..., min_length=1, max_length=256)
    bounds: Bounds
    city: str = Field(..., min_length=1, max_length=256)
    portfolio_url: str = Field(..., min_length=1, max_length=2048)
    with_email_drafts: bool = True,
    max_reviews: int = 10
    min_rating: int = 4


class GenerateLeadsResponse(BaseModel):
    job_id: uuid.UUID


# --- Job Status / Polling ---


class LeadOut(BaseModel):
    business_name: str
    website: str
    email_found: str | None
    reviews: int
    rating: int
    ai_email_draft: str | None


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    leads: list[LeadOut] = []
    city: str
    sector: str
    error_message: str | None = None

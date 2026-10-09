"""Models shared by agents, workers and (via generated zod schemas) the web app."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    uri: str
    page: int | None = None
    kind: Literal["text", "image", "table", "web"]


class ProductFactSheet(BaseModel):
    product_name: str
    product_line: str | None = None
    price_usd: float
    promo: str | None = Field(None, description="e.g. '20% off until Jun 30'")
    key_features: list[str]
    specs: dict[str, str] = {}
    audience: str
    launch_date: date | None = None
    sources: list[Citation]


class JudgeVerdict(BaseModel):
    status: Literal["pass", "fail"]
    gaps: list[str] = []


class ClaimCheck(BaseModel):
    claim: str
    verdict: Literal["supported", "unsupported", "corrected"]
    sources: list[Citation]
    revision: str | None = None


class JournalistMatch(BaseModel):
    journalist_id: UUID
    score: float
    reason: str


# Everything exported to TypeScript. Add new shared models here.
EXPORTED_MODELS: list[type[BaseModel]] = [
    Citation,
    ProductFactSheet,
    JudgeVerdict,
    ClaimCheck,
    JournalistMatch,
]

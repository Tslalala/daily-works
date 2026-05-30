from datetime import datetime

from pydantic import BaseModel, Field


class TargetCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = None
    target_type: str = Field(default="short_term", pattern=r"^(deadline|long_term|short_term)$")
    deadline: datetime | None = None
    priority: int = Field(default=2, ge=1, le=3)


class TargetUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    target_type: str | None = Field(None, pattern=r"^(deadline|long_term|short_term)$")
    deadline: datetime | None = None
    priority: int | None = Field(None, ge=1, le=3)
    status: str | None = Field(None, pattern=r"^(active|completed|archived)$")
    progress: int | None = Field(None, ge=0, le=100)


class MilestoneCreate(BaseModel):
    title: str = Field(..., max_length=200)
    suggested_date: datetime | None = None
    sort_order: int = 0

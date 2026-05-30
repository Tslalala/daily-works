from pydantic import BaseModel, Field


class HabitCreate(BaseModel):
    name: str = Field(..., max_length=200)
    icon: str = "📌"
    description: str | None = None
    frequency: str = Field(default="daily", pattern=r"^(daily|weekly)$")


class HabitUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    icon: str | None = None
    description: str | None = None
    frequency: str | None = Field(None, pattern=r"^(daily|weekly)$")
    status: str | None = Field(None, pattern=r"^(active|archived)$")

from pydantic import BaseModel, Field


class AISuggestRequest(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = ""


class AIRefineRequest(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = ""
    feedback: str = Field(..., max_length=500)


class SetKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    api_base: str = ""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1)
    task_type: Literal["query", "document"]

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, value: list[str]) -> list[str]:
        if not all(item.strip() for item in value):
            raise ValueError("Пустые строки не поддерживаются.")
        return value


class EmbedResponse(BaseModel):
    model_id: str
    quantization: str
    dimensions: int
    vectors: list[list[float]]


class EmbedderHealthResponse(BaseModel):
    status: str
    model_id: str
    quantization: str
    device: str

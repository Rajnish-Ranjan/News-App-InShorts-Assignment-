from pydantic import BaseModel, Field, field_validator

VALID_CATEGORIES = {
    "technology",
    "business",
    "sports",
    "general",
    "politics",
    "entertainment",
    "science",
    "health",
    "world",
    "national",
    "environment",
    "education",
    "lifestyle",
    "automobile",
    "miscellaneous",
}


class PaginationParams(BaseModel):
    limit: int = Field(5, ge=1, le=20)
    cursor: str | None = Field(None)


class CategoryParams(PaginationParams):
    category: str = Field(...)

    @field_validator("category")
    @classmethod
    def normalize_and_validate(cls, v: str) -> str:
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("empty category")
        if normalized not in VALID_CATEGORIES:
            raise ValueError(f"unknown category: {v}")
        return normalized


class ScoreParams(PaginationParams):
    threshold: float = Field(..., ge=0.0, le=1.0)


class SourceParams(PaginationParams):
    source: str = Field(..., min_length=1)

    @field_validator("source")
    @classmethod
    def normalize_and_validate(cls, v: str) -> str:
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("empty source")
        return normalized


class NearbyParams(PaginationParams):
    radius: float = Field(10.0, gt=0, le=500)  # km


class SearchParams(PaginationParams):
    query: str = Field(..., min_length=1)

    @field_validator("query")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("empty query")
        return v


class SmartSearchParams(PaginationParams):
    query: str = Field(..., min_length=1)

    @field_validator("query")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("empty query")
        return v

